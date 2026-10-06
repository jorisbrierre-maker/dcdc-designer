import streamlit as st
import numpy as np
import plotly.graph_objects as plotly_go
from plotly.subplots import make_subplots
from engine import BuckConverterEngine as bce

# Configuration de la page Streamlit pour un design épuré
st.set_page_config(
    page_title="Buck Converter Designer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé pour un look très professionnel
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .sidebar .sidebar-content { background: #ffffff; }
    h1, h2, h3 { color: #1f2937; }
    .stAlert { border-radius: 8px; }
    .metric-container {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.header("Paramètres Opérationnels")

col_vin1, col_vin2 = st.sidebar.columns(2)
vin_min = col_vin1.number_input("Vin min (V)", min_value=1.0, value=10.0, step=0.1, format="%.2f")
vin_max = col_vin2.number_input("Vin max (V)", min_value=float(vin_min), value=20.0, step=0.1, format="%.2f")
vin_typ = st.sidebar.slider("Vin typique (V) pour analyse", min_value=float(vin_min), max_value=float(vin_max), value=12.0, step=0.1)

vout = st.sidebar.number_input("Vout (V)", min_value=0.1, value=5.0, step=0.1, format="%.2f")
iout = st.sidebar.number_input("Courant de sortie Iout (A)", min_value=0.01, value=2.0, step=0.01, format="%.2f")
kr = st.sidebar.slider("Ratio Ondulation Courant (Kr)", min_value=0.1, max_value=1.0, value=0.4, step=0.05, format="%.2f")

st.sidebar.header("Caractéristiques Contrôleur")
fsw_khz = st.sidebar.number_input("Fréquence découpage Fsw (kHz)", min_value=10, value=500, step=10, format="%d")
fsw = fsw_khz * 1e3
vfb = st.sidebar.number_input("Tension de Référence Vfb (V)", min_value=0.01, value=0.8, step=0.01, format="%.3f")
current_limit = st.sidebar.number_input("Limite de Courant (Saturation) (A)", min_value=0.1, value=4.0, step=0.1, format="%.2f")


# --- VÉRIFICATION PHYSIQUE DE BASE ---
if vout >= vin_min:
    st.error(f"Erreur : Vout ({vout}V) doit être strictement inférieur à Vin min ({vin_min}V) pour un convertisseur Buck.")
    st.stop()


# --- SECTION 1 : DIMENSIONNEMENT THÉORIQUE ---
st.header("Dimensionnement Théorique Recommandé")
st.markdown(f"Valeurs calculées pour un point de fonctionnement optimal (Ondulation cible de {kr*100:.0f}% du courant DC).")

ideal_l_nom = bce.get_ideal_inductor(vout, vin_typ, fsw, iout, ripple_factor=kr)
ideal_l = ideal_l_nom # For backward compatibility with the rest of the file
i_dc_max_safe = current_limit / (1.0 + (kr / 2.0))
ideal_l_min = bce.get_ideal_inductor(vout, vin_typ, fsw, i_dc_max_safe, ripple_factor=kr)

duty_cycle_typ = bce.calculate_duty_cycle(vout, vin_typ)

col1a, col1b = st.columns(2)

col1a.metric("L Idéale (Charge nominale)", f"{ideal_l_nom * 1e6:.2f} µH", delta="Basé sur Iout", delta_color="off")
with col1a.expander("Détail du calcul nominal"):
    st.caption("Inductance optimisée pour le courant de sortie prévu.")
    st.latex(r"L = \frac{V_{out} \cdot (V_{in} - V_{out})}{V_{in} \cdot F_{sw} \cdot (I_{out} \cdot K_R)}")
    st.latex(rf"L = \frac{{{vout} \cdot ({vin_typ} - {vout})}}{{{vin_typ} \cdot {fsw_khz}\text{{k}} \cdot ({iout} \cdot {kr})}}")

col1b.metric("L Minimale (Limite Puce)", f"{ideal_l_min * 1e6:.2f} µH", delta="Basé sur Limite Saturation", delta_color="inverse")
with col1b.expander("Détail de la Marge Ripple"):
    st.caption("Inductance minimale pour ne pas déclencher la sécurité. On déduit d'abord le courant continu max sûr (I_DC_Max_Safe) pour laisser la place à l'ondulation.")
    st.latex(r"I_{DC\_Max\_Safe} = \frac{I_{sat}}{1 + \frac{K_R}{2}}")
    st.latex(rf"I_{{DC\_Max\_Safe}} = \frac{{{current_limit}}}{{1 + \frac{{{kr}}}{{2}}}} = {i_dc_max_safe:.2f}\text{{ A}}")
    st.latex(r"L_{min} = \frac{V_{out} \cdot (V_{in} - V_{out})}{V_{in} \cdot F_{sw} \cdot (I_{DC\_Max\_Safe} \cdot K_R)}")

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

col1.empty() # Placeholder since col1 is now used above. Actually let's just use col2, col3, col4

col2.metric("Rapport Cyclique (D)", f"{duty_cycle_typ * 100:.1f} %")
with col2.expander("Détail du calcul"):
    st.latex(r"D = \frac{V_{out}}{V_{in}}")
    st.latex(rf"D = \frac{{{vout}}}{{{vin_typ}}}")

col3.metric("I_Cin (RMS) max", f"{bce.calculate_cin_rms_current(iout, 0.5):.2f} A")
with col3.expander("Détail du calcul"):
    st.caption("Pire cas à D = 0.5")
    st.latex(r"I_{Cin(RMS)} = I_{out} \cdot \sqrt{D \cdot (1 - D)}")
    st.latex(rf"I_{{Cin(RMS)}} = {iout} \cdot \sqrt{{0.5 \cdot 0.5}}")

col4.metric("Feedback R ratio (R1/R2)", f"{(vout/vfb) - 1:.2f}")
with col4.expander("Détail du calcul"):
    st.latex(r"\frac{R_1}{R_2} = \frac{V_{out}}{V_{FB}} - 1")
    st.latex(rf"\frac{{R_1}}{{R_2}} = \frac{{{vout}}}{{{vfb}}} - 1")


# --- SECTION 2 : ANALYSE WHAT-IF (DESIGN MANUEL) ---
st.header("Analyse de Sensibilité (What-If)")
st.markdown("Ajustez les composants commerciaux pour observer l'impact réel.")

with st.container():
    col_w1, col_w2, col_w3 = st.columns(3)
    
    with col_w1:
        st.subheader("Inductance (L)")
        l_uh = st.number_input("L choisie (µH)", min_value=0.01, value=round(ideal_l*1e6, 2), step=0.1, format="%.2f")
        l_val = l_uh * 1e-6
        
    with col_w2:
        st.subheader("Condensateurs (C)")
        cin_uf = st.number_input("Cin choisie (µF)", min_value=0.1, value=22.0, step=1.0, format="%.1f")
        cin_val = cin_uf * 1e-6
        cout_uf = st.number_input("Cout choisie (µF)", min_value=0.1, value=47.0, step=1.0, format="%.1f")
        cout_val = cout_uf * 1e-6
        
    with col_w3:
        st.subheader("Réseau Feedback")
        r1_k = st.number_input("R1 (kΩ) - Haut", min_value=0.1, value=10.0, step=0.1, format="%.2f")
        r1_val = r1_k * 1e3
        r2_val = bce.calculate_feedback_resistor(r1_val, vout, vfb)
        st.markdown(f"**R2 calculée : {r2_val / 1e3:.2f} kΩ**")
        with st.expander("Détail du calcul"):
            st.latex(r"R_2 = \frac{R_1}{\frac{V_{out}}{V_{FB}} - 1}")
            st.latex(rf"R_2 = \frac{{{r1_k}\text{{k}}}}{{\frac{{{vout}}}{{{vfb}}} - 1}}")
            
        st.markdown("---")
        st.subheader("Feedforward ($C_{ff}$)")
        fc_khz = st.number_input("Fréquence coupure Fc (kHz)", min_value=1.0, value=float(fsw_khz/10), step=1.0, help="Typiquement Fsw / 10 (voir Datasheet de la puce).")
        fc = fc_khz * 1e3
        
        ideal_cff = bce.calculate_ideal_cff(r1_val, fc)
        st.markdown(f"**$C_{{ff}}$ Idéal : {ideal_cff * 1e12:.0f} pF**")
        
        cff_pf = st.number_input("$C_{ff}$ choisi (pF)", min_value=0.0, value=float(round(ideal_cff * 1e12)), step=1.0, help="Simulez le changement de condensateur lors d'un double sourcing.")
        cff_val = cff_pf * 1e-12
        
        if cff_val > 0:
            fz = bce.calculate_fz(r1_val, cff_val)
            fz_khz = fz / 1e3
            
            if fz < fc / 2:
                st.error(f"**$F_z$ = {fz_khz:.1f} kHz**\n\n$C_{{ff}}$ trop grand ! Zéro trop bas. Grand risque d'instabilité (injection bruit HF).")
            elif fz > fc * 2:
                st.warning(f"**$F_z$ = {fz_khz:.1f} kHz**\n\n$C_{{ff}}$ trop petit. Inefficace, n'apporte pas le boost de phase attendu à $F_c$.")
            else:
                st.success(f"**$F_z$ = {fz_khz:.1f} kHz**\n\nParfait ! Zéro proche de $F_c$. Marge de phase optimale pour les transitoires.")
                
            with st.expander("Détail du calcul"):
                st.latex(r"F_z = \frac{1}{2 \pi \cdot R_1 \cdot C_{ff}}")
                st.latex(rf"F_z = \frac{{1}}{{2 \pi \cdot {r1_k}\text{{k}} \cdot {cff_pf}\text{{p}}}}")

# --- CALCULS EN TEMPS RÉEL (WHAT-IF) ---
delta_il = bce.calculate_inductor_ripple(vout, vin_typ, fsw, l_val)
ripple_pct = (delta_il / iout) * 100 if iout > 0 else 0

peak_i, valley_i = bce.calculate_inductor_currents(iout, delta_il)
delta_vout = bce.calculate_vout_ripple_ceramic(vout, duty_cycle_typ, fsw, l_val, cout_val)
delta_vin = bce.calculate_vin_ripple(iout, fsw, cin_val, duty_cycle_typ)

# --- ALERTES ET MÉTRIQUES DYNAMIQUES ---
st.markdown("### Performances avec les composants choisis")
m_col1, m_col2, m_col3 = st.columns(3)

# Ripple Alert
with m_col1:
    st.markdown("**Ondulation Self**")
    if ripple_pct < 20 or ripple_pct > 60:
        st.warning(f"{delta_il:.2f}A ({ripple_pct:.1f}%)")
    else:
        st.success(f"{delta_il:.2f}A ({ripple_pct:.1f}%)")
    with st.expander("Détail du calcul"):
        st.latex(r"\Delta I_L = \frac{V_{out} \cdot (V_{in} - V_{out})}{V_{in} \cdot F_{sw} \cdot L}")
        st.latex(rf"\Delta I_L = \frac{{{vout} \cdot ({vin_typ} - {vout})}}{{{vin_typ} \cdot {fsw_khz}\text{{k}} \cdot {l_uh:.2f}\mu}}")

# Peak Current Alert
with m_col2:
    st.markdown("**Courant Crête**")
    if peak_i >= current_limit:
        st.error(f"{peak_i:.2f}A (Sature à {current_limit}A)")
    elif peak_i >= current_limit * 0.8:
        st.warning(f"{peak_i:.2f}A (Proche saturation)")
    else:
        st.success(f"{peak_i:.2f}A")
    with st.expander("Détail du calcul"):
        st.latex(r"I_{peak} = I_{out} + \frac{\Delta I_L}{2}")
        st.latex(rf"I_{{peak}} = {iout} + \frac{{{delta_il:.2f}}}{{2}}")

# Vout Ripple Alert
with m_col3:
    st.markdown("**Ondulation Vout**")
    vout_ripple_pct = (delta_vout / vout) * 100
    if vout_ripple_pct > 2.0:
        st.error(f"{delta_vout*1000:.1f}mV ({vout_ripple_pct:.2f}%)")
    elif vout_ripple_pct > 1.0:
        st.warning(f"{delta_vout*1000:.1f}mV ({vout_ripple_pct:.2f}%)")
    else:
        st.success(f"{delta_vout*1000:.1f}mV ({vout_ripple_pct:.2f}%)")
    with st.expander("Détail du calcul"):
        st.caption("Formule simplifiée (Condensateur Céramique)")
        st.latex(r"\Delta V_{out} = \frac{V_{out} \cdot (1 - D)}{8 \cdot F_{sw}^2 \cdot L \cdot C_{out}}")
        st.latex(rf"\Delta V_{{out}} = \frac{{{vout} \cdot (1 - {duty_cycle_typ:.3f})}}{{8 \cdot ({fsw_khz}\text{{k}})^2 \cdot {l_uh:.2f}\mu \cdot {cout_uf:.1f}\mu}}")

st.markdown("### Réactivité & Transitoires")

t_col1, t_col2 = st.columns([1, 2])
with t_col1:
    load_step = st.number_input("Échelon Courant Brutal (A)", min_value=0.01, max_value=float(current_limit), value=round(iout/2, 2), step=0.1, format="%.2f", help="Simule un composant qui se réveille instantanément.")

r_col1, r_col2 = st.columns(2)
sr_up, sr_down = bce.calculate_slew_rate(vin_typ, vout, l_val)
sag = bce.calculate_voltage_sag(vin_typ, vout, l_val, cout_val, load_step)

with r_col1:
    st.markdown("**Slew Rate (Montée)**")
    st.info(f"**{sr_up:.2f} A/µs** (Vitesse physique max de la self)")
    with st.expander("Détail du calcul"):
        st.latex(r"SR = \frac{V_{in} - V_{out}}{L}")
        st.latex(rf"SR = \frac{{{vin_typ} - {vout}}}{{{l_uh:.2f}\mu}}")
with r_col2:
    st.markdown("**Chute de tension estimée (Sag)**")
    if sag > 0.05 * vout:
        st.error(f"**{sag*1000:.0f} mV** (Système trop lent !)")
    elif sag > 0.02 * vout:
        st.warning(f"**{sag*1000:.0f} mV**")
    else:
        st.success(f"**{sag*1000:.0f} mV**")
    with st.expander("Détail du calcul"):
        st.latex(r"\Delta V = \frac{L \cdot \Delta I^2}{2 \cdot C_{out} \cdot (V_{in} - V_{out})}")
        st.latex(rf"\Delta V = \frac{{{l_uh:.2f}\mu \cdot {load_step}^2}}{{2 \cdot {cout_uf:.1f}\mu \cdot ({vin_typ} - {vout})}}")


# --- SECTION 3 : DASHBOARDS VISUELS ---
st.header("Dashboards Visuels")

tab0, tab1, tab2, tab3, tab4 = st.tabs(["Chronogrammes Temporels", "Ondulation Courant vs Inductance", "Courants vs Vin", "Ripple Sortie vs Fréquence", "Réactivité (Voltage Sag)"])

with tab0:
    waveforms = bce.generate_time_waveforms(vin_typ, vout, fsw, l_val, cout_val, iout, num_cycles=3, points_per_cycle=1000)
    t_us = waveforms["t"] * 1e6
    
    fig_time = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Tensions (Axe Primaire)
    fig_time.add_trace(plotly_go.Scatter(x=t_us, y=waveforms["v_sw"], mode='lines', name='V_SW (Tension commutation)', line=dict(color='gray', width=1.5, dash='dot')), secondary_y=False)
    fig_time.add_trace(plotly_go.Scatter(x=t_us, y=waveforms["v_out"], mode='lines', name='V_out (Ondulation sortie)', line=dict(color='#2ca02c', width=3)), secondary_y=False)
    
    # Courants (Axe Secondaire)
    fig_time.add_trace(plotly_go.Scatter(x=t_us, y=waveforms["i_l"], mode='lines', name='I_L (Courant Inductance)', line=dict(color='#1f77b4', width=2)), secondary_y=True)
    fig_time.add_trace(plotly_go.Scatter(x=t_us, y=waveforms["i_cin"], mode='lines', name='I_Cin (Courant pulsé entrée)', line=dict(color='#d62728', width=2)), secondary_y=True)
    
    fig_time.update_layout(title="Chronogrammes Temporels (Simulation idéale CCM)", xaxis_title="Temps (µs)", template="plotly_white", hovermode="x unified")
    fig_time.update_yaxes(title_text="Tension (V)", secondary_y=False)
    fig_time.update_yaxes(title_text="Courant (A)", secondary_y=True)
    
    st.plotly_chart(fig_time, use_container_width=True)

with tab1:
    l_arr_uh = np.linspace(max(0.1, l_uh / 5), l_uh * 3, 100)
    l_arr = l_arr_uh * 1e-6
    ripple_arr = bce.calculate_inductor_ripple(vout, vin_typ, fsw, l_arr)
    
    fig_l = plotly_go.Figure()
    fig_l.add_trace(plotly_go.Scatter(x=l_arr_uh, y=ripple_arr, mode='lines', name='Δ IL', line=dict(color='#1f77b4', width=3)))
    fig_l.add_vline(x=l_uh, line_dash="dash", line_color="red", annotation_text="L Choisie")
    fig_l.add_hline(y=iout*0.4, line_dash="dot", line_color="green", annotation_text="Cible 40%")
    fig_l.update_layout(title="Impact de l'Inductance sur l'ondulation de courant", xaxis_title="Inductance (µH)", yaxis_title="Ondulation Peak-to-Peak (A)", template="plotly_white")
    st.plotly_chart(fig_l, use_container_width=True)

with tab2:
    vin_arr = np.linspace(vin_min, vin_max, 50)
    peak_arr = []
    valley_arr = []
    rms_cin_arr = []
    for v in vin_arr:
        d = bce.calculate_duty_cycle(vout, v)
        r = bce.calculate_inductor_ripple(vout, v, fsw, l_val)
        p, vl = bce.calculate_inductor_currents(iout, r)
        peak_arr.append(p)
        valley_arr.append(vl)
        rms_cin_arr.append(bce.calculate_cin_rms_current(iout, d))
        
    fig_i = plotly_go.Figure()
    fig_i.add_trace(plotly_go.Scatter(x=vin_arr, y=peak_arr, mode='lines', name='Courant Crête (Peak)', fill='tonexty', fillcolor='rgba(255, 99, 71, 0.2)'))
    fig_i.add_trace(plotly_go.Scatter(x=vin_arr, y=[iout]*len(vin_arr), mode='lines', name='Courant Nominal Iout', line=dict(dash='dash')))
    fig_i.add_trace(plotly_go.Scatter(x=vin_arr, y=valley_arr, mode='lines', name='Courant Vallée', fill='tonexty', fillcolor='rgba(135, 206, 250, 0.2)'))
    fig_i.add_trace(plotly_go.Scatter(x=vin_arr, y=rms_cin_arr, mode='lines', name='I_Cin (RMS)', line=dict(color='purple')))
    fig_i.add_hline(y=current_limit, line_dash="dash", line_color="red", annotation_text="Limite Saturation")
    
    fig_i.update_layout(title="Évolution des courants en fonction de Vin", xaxis_title="Vin (V)", yaxis_title="Courant (A)", template="plotly_white")
    st.plotly_chart(fig_i, use_container_width=True)

with tab3:
    fsw_arr_khz = np.linspace(100, 2000, 100)
    fsw_arr = fsw_arr_khz * 1e3
    # Vout ripple formula ceramic simplified:
    # dV = Vout*(1-D) / (8*Fsw^2*L*Cout)
    dvout_arr = (vout * (1 - duty_cycle_typ)) / (8 * (fsw_arr**2) * l_val * cout_val)
    
    fig_v = plotly_go.Figure()
    fig_v.add_trace(plotly_go.Scatter(x=fsw_arr_khz, y=dvout_arr * 1000, mode='lines', name='Δ Vout', line=dict(color='#ff7f0e', width=3)))
    fig_v.add_vline(x=fsw_khz, line_dash="dash", line_color="red", annotation_text="Fsw Choisie")
    fig_v.update_layout(title="Impact de la fréquence sur l'ondulation de tension (Céramique)", xaxis_title="Fréquence de découpage (kHz)", yaxis_title="Ondulation de sortie (mV)", template="plotly_white", yaxis_type="log")
    st.plotly_chart(fig_v, use_container_width=True)

with tab4:
    l_arr_uh = np.linspace(max(0.1, l_uh / 5), l_uh * 5, 100)
    l_arr = l_arr_uh * 1e-6
    sag_arr = bce.calculate_voltage_sag(vin_typ, vout, l_arr, cout_val, load_step)
    
    fig_sag = plotly_go.Figure()
    fig_sag.add_trace(plotly_go.Scatter(x=l_arr_uh, y=sag_arr * 1000, mode='lines', name='Voltage Sag', line=dict(color='#d62728', width=3)))
    fig_sag.add_vline(x=l_uh, line_dash="dash", line_color="red", annotation_text="L Choisie")
    fig_sag.update_layout(title=f"Impact de l'Inductance sur la chute de tension (Saut brutal de {load_step}A)", xaxis_title="Inductance (µH)", yaxis_title="Chute de tension minimale théorique (mV)", template="plotly_white")
    st.plotly_chart(fig_sag, use_container_width=True)
