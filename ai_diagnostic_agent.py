import socket
import json
import time
import streamlit as st # Streamlit alustus
import ollama

# UDP-konfiguraatio simulaattorin kuunteluun
AI_LISTEN_PORT = 45456

EXCAVATOR_MANUAL = """ 
VIKAVAIHTOEHDOT JA HUOLTO-OHJEET - KAIVURI M180: 
1. YLIKUUMENEMISVAROITUS (OVERHEAT WARNING): Jos moottorin lämpötila ylittää 98 astetta, laite on asetettava heti tyhjäkäynnille. Älä sammuta moottoria välittömästi, jotta jäähdytysneste kiertää. Tarkista jäähdyttimen ritilät tukosten varalta. 
2. KORKEA PAINE (HIGH PRESSURE OPERATION): Jos hydrauliikkapaine ylittää 230 bar, tarkista päävaroventtiilin säätö. Mikäli paine nousee yli 300 bar, järjestelmä laukaisee hätäpysäytyksen letkurikon estämiseksi. 
3. HÄTÄPYSÄYTYS (EMERGENCY STOP ACTIVE): Hätäpysäytyksen jälkeen järjestelmä on nollattava pääohjauspaneelista (koodi E-STOP RESET). Tarkista ennen nollausta, ettei hydrauliikkavuotoja ole. 
""" 

# Alustetaan Streamlitin muuttujat 
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = [] 
    
if "live_data" not in st.session_state: 
    st.session_state.live_data = { 
        "motorRpm": 0, 
        "engineTemperature": 45.0, 
        "hydraulicPressure": 120.0, 
        "motorLoad": 0, 
        "bucketAngle": 0.0, 
        "emergencyStop": False 
    } 

# Aikaleiman alustus simulaattorin katkoksen seurantaan 
if "last_packet_time" not in st.session_state: 
    st.session_state.last_packet_time = time.time() 
            
# Alustetaan globaali socket-yhteys verkkoporttiin 
@st.cache_resource
def get_udp_socket():   #if "udp_socket" not in st.session_state: 
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    sock.bind(('127.0.0.1', AI_LISTEN_PORT)) 
    sock.setblocking(False)
    return sock 
    
st.session_state.udp_socket = get_udp_socket()#sock 

# 3. STREAMLIT SIVUN RAKENNE ---
st.set_page_config(page_title="AI Diagnostiikkakeskus", page_icon="🛠️", layout="wide")

st.title("🛠️ Teollisuuskoneen AI-Diagnostiikka & Huoltokeskus")
st.subheader("Kaivuri M180 - Reaaliaikainen RAG-vianmääritysjärjestelmä")

# Jaetaan sivu kahteen sarakkeeseen: Vasen = Telemetria & Opus, Oikea = AI Chat
col1, col2 = st.columns([1, 1.2])

# --- SARAKE 1: MITTARISTO (ITSENÄINEN FRAGMENTTI) --- 
with col1: 
    @st.fragment(run_every=0.5)
    def nayta_live_telemetria():
        st.header("🖥️ Koneen Live-Telemetria") 
        
        sock = st.session_state.udp_socket
        tel = st.session_state.live_data
        uutta_dataa_tuli = False

        # Luetaan UDP-portti tyhjäksi asti 
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                tel = json.loads(data.decode('utf-8'))
                st.session_state.live_data = tel
                uutta_dataa_tuli = True
            except (BlockingIOError, OSError):
                break

        # Jos simulaattori lähetti jotain, päivitetään aikaleima 
        if uutta_dataa_tuli:
            st.session_state.last_packet_time = time.time()

        # Lasketaan onko simulaattori pysähtynyt (hiljentynyt yli 1.0 sekunniksi) 
        aikaa_kulunut = time.time() - st.session_state.last_packet_time 
        simulaattori_pysähtynyt = aikaa_kulunut > 1.0 
        
        # Määritetään tilat (jos simulaattori pysähtyy, pakotetaan hätä-seis päälle!) 
        is_estop = tel.get("emergencyStop", False) or simulaattori_pysähtynyt 
        is_overheat = tel.get("engineTemperature", 45.0) > 98.0 and not simulaattori_pysähtynyt 
        is_high_press = tel.get("hydraulicPressure", 120.0) > 230.0 and not simulaattori_pysähtynyt 
    
        # Hälytysbannerit
        if is_estop: 
            st.error("🚨 HÄTÄPYSÄYTYS AKTIIVINEN (EMERGENCY STOP ACTIVE)") 
        elif is_overheat: 
            st.error("⚠️ MOOTTORIN YLIKUUMENEMISVAROITUS (OVERHEAT WARNING)") 
        elif is_high_press: 
            st.warning("⚠️ HYDRAULIIKAN KORKEA PAINE (HIGH PRESSURE OPERATION)") 
        else: 
            st.success("✅ JÄRJESTELMÄN TILA: OK") 
   
        # Mittarit siistissä ruudukossa 
        m1, m2 = st.columns(2) 
        m1.metric("Moottorin lämpötila", f"{tel.get('engineTemperature', 45.0):.1f} °C", delta="- Ylikuumenee!" if is_overheat else None, delta_color="inverse") 
        m2.metric("Hydrauliikan paine", f"0.0 bar" if simulaattori_pysähtynyt else f"{tel.get('hydraulicPressure', 120.0):.1f} bar", delta="- Korkea paine!" if is_high_press else None, delta_color="inverse") 
                 
        m3, m4 = st.columns(2) 
        m3.metric("Moottorin kierrosluku", f"0 RPM" if simulaattori_pysähtynyt else f"{tel.get('motorRpm', 0)} RPM") 
        m4.metric("Kauhan kulma", f"{tel.get('bucketAngle', 0.0):.1f} °")   
        
        # Digitaalinen avattava huolto-opas pidetään fragmentin sisällä
        with st.expander("📖 Katso laitteen digitaalista huolto-opasta (RAG-tietokanta)"): 
            st.text(EXCAVATOR_MANUAL)

    nayta_live_telemetria()

    # Chatin tyhjennyspainike pidetään fragmentin ulkopuolella 
    st.write("---")
    if st.button("🗑️ Tyhjennä chatin historia", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# --- SARAKE 2: TEKOÄLY CHAT (OMANA FRAGMENTTINAAN) --- 
with col2: 
    @st.fragment 
    def nayta_ai_chat(): 
        st.header("🤖 Älykäs Huolto-apuri (Gemma 2)") 
        st.write("Kysy tekoälyltä ohjeita vian korjaamiseen. Se analysoi automaattisesti yllä olevan datan ja huolto-oppaan.") 
    
        # Tulostetaan chat-historia 
        for msg in st.session_state.chat_history: 
            with st.chat_message(msg["role"]): 
                st.write(msg["content"]) 
    
        # Käyttäjän syötekenttä 
        if user_query := st.chat_input("Esim. Moottorin lämpötila on liian korkea, mitä teen?"): 
            st.session_state.chat_history.append({"role": "user", "content": user_query}) 
            st.rerun() # Päivitetään chat-näkymä heti, jotta käyttäjän viesti ilmestyy ruudulle  

    nayta_ai_chat()

    # Lähetetään kysymys Ollamalle vain silloin, kun uusi viesti on lisätty historiaan 
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user": 
        user_query = st.session_state.chat_history[-1]["content"] 
 
        with st.chat_message("assistant"): 
            with st.spinner("AI analysoi laitteen tilaa lennosta..."):

                live_tel = st.session_state.get("live_data", {}) 
                aikaa_kulunut = time.time() - st.session_state.get("last_packet_time", time.time()) 
                simulaattori_pysähtynyt = aikaa_kulunut > 1.0 
                                
                current_rpm = 0 if simulaattori_pysähtynyt else live_tel.get('motorRpm', 0) 
                current_temp = round(live_tel.get('engineTemperature', 45.0), 1) 
                current_press = 0.0 if simulaattori_pysähtynyt else round(live_tel.get('hydraulicPressure', 120.0), 1) 
                current_angle = round(live_tel.get('bucketAngle', 0.0), 1) 
                current_estop = simulaattori_pysähtynyt 
               
                # Muotoillaan LLM-prompt 
                system_prompt = (
                    "Olet teollisuuskoneiden huolto-apuri. Vastaa lyhyesti ja asiantuntevasti, selkeästi ja virheettömällä suomen kielellä.\n" 
                    f"Koneen reaaliaikaiset mittarilukemat ovat nyt:\n"
                    f"- Moottorin lämpötila: {current_temp} °C\n"
                    f"- Hydrauliikan paine: {current_press} bar\n" 
                    f"- Moottorin kierrosluku: {current_rpm} RPM\n" 
                    f"- Hätä-Pysäytys aktiivinen: {current_estop}\n\n" 
                    "Käytä vastauksessasi TÄSMÄLLEEN yllä olevia lukuja, jos mainitset lukemia. Älä pyöristä tai muuta niitä lukuja itse!\n" 
                    "Käytä annetun huolto-oppaan valmiita ohjeita ja lauseita vian korjaamiseen."
                ) 

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"HUOLTO-OPAS:\n{EXCAVATOR_MANUAL}\n\nKysymys: {user_query}"}
                ]

                try:
                    stream = ollama.chat(model='gemma2:2b', messages=messages, stream=True)
                                        
                    def generaattori():
                        for chunk in stream:
                            yield chunk['message']['content']
                    
                    ai_response = st.write_stream(generaattori)
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                    st.rerun() # Päivitetään sivu lopullisesti viestin tallennuksen jälkeen

                except Exception as e: 
                    st.write(f"Virhe Ollama-yhteydessä: {e}") 

                