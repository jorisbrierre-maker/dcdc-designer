import numpy as np
from typing import Dict, Any, Tuple

class BuckConverterEngine:
    """
    Moteur de calcul physique pour le dimensionnement d'un convertisseur DC/DC Buck.
    Toutes les unités sont en unités du SI (Volts, Ampères, Hertz, Farads, Henrys, Ohms).
    """

    @staticmethod
    def calculate_duty_cycle(vout: float, vin: float) -> float:
        """Calcule le rapport cyclique."""
        if vin <= 0 or vout > vin:
            return 0.0 # Cas impossible physiquement pour un buck normal sans pertes
        return vout / vin

    @staticmethod
    def calculate_feedback_resistor(r1: float, vout: float, vfb: float) -> float:
        """Calcule R2 en fonction de R1, Vout et Vfb."""
        if vout <= vfb:
            return float('inf') # Pas de diviseur nécessaire ou impossible
        return r1 / ((vout / vfb) - 1.0)

    @staticmethod
    def calculate_inductor_ripple(vout: float, vin: float, fsw: float, l: float) -> float:
        """Calcule l'ondulation de courant dans l'inductance (Peak-to-Peak)."""
        if np.isscalar(vin) and np.isscalar(fsw) and np.isscalar(l):
            if vin == 0 or fsw == 0 or l == 0:
                return 0.0
        return (vout * (vin - vout)) / (vin * fsw * l)

    @staticmethod
    def calculate_inductor_currents(iout: float, delta_il: float) -> Tuple[float, float]:
        """Calcule le courant crête (Peak) et vallée (Valley) de l'inductance."""
        peak = iout + (delta_il / 2.0)
        valley = max(0.0, iout - (delta_il / 2.0)) # CCM ou DCM boundary
        return peak, valley

    @staticmethod
    def calculate_cin_rms_current(iout: float, d: float) -> float:
        """Calcule le courant RMS traversant le condensateur d'entrée."""
        return iout * np.sqrt(d * (1.0 - d))

    @staticmethod
    def calculate_vin_ripple(iout: float, fsw: float, cin: float, d: float) -> float:
        """Calcule l'ondulation de tension en entrée."""
        if fsw == 0 or cin == 0:
            return 0.0
        return (iout / (fsw * cin)) * d * (1.0 - d)

    @staticmethod
    def calculate_vout_ripple(delta_il: float, fsw: float, cout: float, esr: float = 0.0) -> float:
        """Calcule l'ondulation de tension en sortie (approximation générale)."""
        if fsw == 0 or cout == 0:
            return 0.0
        return delta_il * (esr + (1.0 / (8.0 * fsw * cout)))

    @staticmethod
    def calculate_vout_ripple_ceramic(vout: float, d: float, fsw: float, l: float, cout: float) -> float:
        """Calcule l'ondulation de tension de sortie (simplification pour condensateurs céramiques)."""
        if fsw == 0 or l == 0 or cout == 0:
            return 0.0
        return (vout * (1.0 - d)) / (8.0 * (fsw ** 2) * l * cout)

    @staticmethod
    def calculate_feedforward_capacitor(r1: float, r2: float, fcross: float) -> float:
        """Calcule la valeur optionnelle du condensateur de feedforward (Cff)."""
        if fcross == 0 or r1 == 0 or r2 == 0:
            return 0.0
        return (r1 + r2) / (2.0 * np.pi * fcross * r1 * r2)

    @staticmethod
    def get_ideal_inductor(vout: float, vin: float, fsw: float, iout: float, ripple_factor: float = 0.4) -> float:
        """Propose une valeur d'inductance idéale basée sur un facteur d'ondulation (ex: 40% de Iout)."""
        target_ripple = iout * ripple_factor
        if target_ripple == 0 or vin == 0 or fsw == 0:
            return 0.0
        return (vout * (vin - vout)) / (vin * fsw * target_ripple)

    @staticmethod
    def generate_ripple_vs_inductance_data(vout: float, vin: float, fsw: float, l_range: np.ndarray) -> np.ndarray:
        """Génère les données pour le graphique Ondulation vs Inductance."""
        return BuckConverterEngine.calculate_inductor_ripple(vout, vin, fsw, l_range)

    @staticmethod
    def generate_vout_ripple_surface(delta_il: float, fsw_range: np.ndarray, cout_range: np.ndarray, esr: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Génère les données pour la surface 3D ou contours Ondulation Sortie vs Fsw & Cout."""
        F, C = np.meshgrid(fsw_range, cout_range)
        Z = delta_il * (esr + (1.0 / (8.0 * F * C)))
        return F, C, Z

    @staticmethod
    def calculate_slew_rate(vin: float, vout: float, l: float) -> Tuple[float, float]:
        """Calcule la vitesse de balayage du courant (Slew Rate) en montée et descente en A/µs."""
        if np.isscalar(l) and l == 0:
            return 0.0, 0.0
        sr_up = ((vin - vout) / l) * 1e-6
        sr_down = (vout / l) * 1e-6
        return sr_up, sr_down

    @staticmethod
    def calculate_voltage_sag(vin: float, vout: float, l: float, cout: float, delta_i: float) -> float:
        """Estime la chute de tension (Voltage Sag) due à un échelon de courant brut."""
        denominator = 2.0 * cout * (vin - vout)
        if isinstance(denominator, np.ndarray) or isinstance(l, np.ndarray):
             return np.where(denominator <= 0, 0.0, (l * (delta_i ** 2)) / denominator)
        else:
             if denominator <= 0: return 0.0
             return (l * (delta_i ** 2)) / denominator

    @staticmethod
    def generate_time_waveforms(vin: float, vout: float, fsw: float, l: float, cout: float, iout: float, num_cycles: int = 3, points_per_cycle: int = 1000) -> Dict[str, np.ndarray]:
        """Génère les vecteurs temporels (CCM) pour tracer les chronogrammes à l'oscilloscope."""
        d = vout / vin
        t_period = 1.0 / fsw
        t_on = d * t_period
        
        total_time = num_cycles * t_period
        total_points = num_cycles * points_per_cycle
        
        t = np.linspace(0, total_time, total_points)
        
        v_sw = np.zeros_like(t)
        i_l = np.zeros_like(t)
        i_cin = np.zeros_like(t)
        
        delta_il = BuckConverterEngine.calculate_inductor_ripple(vout, vin, fsw, l)
        i_valley = iout - (delta_il / 2.0)
        i_peak = iout + (delta_il / 2.0)
        
        # Optimisation vectorielle avec numpy
        t_mod = t % t_period
        on_phase = t_mod <= t_on
        off_phase = t_mod > t_on
        
        # 1. Tension au noeud de commutation V_SW
        v_sw[on_phase] = vin
        v_sw[off_phase] = 0.0
        
        # 2. Courant dans l'inductance I_L
        i_l[on_phase] = i_valley + ((vin - vout) / l) * t_mod[on_phase]
        i_l[off_phase] = i_peak - (vout / l) * (t_mod[off_phase] - t_on)
        
        # (Sécurité basique pour émuler le Discontinuous Conduction Mode si Iout est très faible)
        i_l[i_l < 0] = 0.0
        
        # 3. Courant d'entrée I_Cin (pulsé)
        i_cin[on_phase] = i_l[on_phase]
        i_cin[off_phase] = 0.0
        
        # 4. Ondulation de la tension de sortie V_out
        i_c = i_l - iout
        dt = t[1] - t[0]
        # Intégration V = 1/C * ∫ i_c dt
        v_out_ripple = np.cumsum(i_c) * dt / cout
        # Centrage sur Vout nominal
        v_out_ripple = v_out_ripple - np.mean(v_out_ripple) + vout

        return {
            "t": t,
            "v_sw": v_sw,
            "i_l": i_l,
            "i_cin": i_cin,
            "v_out": v_out_ripple
        }

    @staticmethod
    def calculate_ideal_cff(r1: float, fc: float) -> float:
        """
        Calcule le condensateur Feedforward (Cff) idéal pour placer le Zéro 
        exactement sur la fréquence de coupure (Crossover Frequency) de la boucle.
        Fz = 1 / (2 * pi * R1 * Cff)
        """
        if r1 <= 0 or fc <= 0:
            return 0.0
        return 1.0 / (2.0 * np.pi * r1 * fc)

    @staticmethod
    def calculate_fz(r1: float, cff: float) -> float:
        """
        Calcule la fréquence du Zéro (Fz) générée par le réseau R1 // Cff.
        """
        if r1 <= 0 or cff <= 0:
            return 0.0
        return 1.0 / (2.0 * np.pi * r1 * cff)

    @staticmethod
    def calculate_psm_frequency(vin: float, vout: float, l: float, i_standby: float, i_peak_min: float) -> float:
        """
        Calcule la fréquence de découpage effective en Pulse Skip Mode (PSM) pour un courant de veille donné.
        Fsw_eff = (2 * I_standby * Vout * (Vin - Vout)) / (L * I_peak_min^2 * Vin)
        """
        if vin <= vout or i_peak_min <= 0 or l <= 0 or vout <= 0:
            return 0.0
        return (2.0 * i_standby * vout * (vin - vout)) / (l * (i_peak_min**2) * vin)

    @staticmethod
    def calculate_psm_voltage_ripple(vin: float, vout: float, l: float, cout: float, i_peak_min: float) -> float:
        """
        Calcule l'ondulation de tension crête-à-crête générée lors d'un burst PSM.
        Vout_ripple_psm = (L * I_peak_min^2 * Vin) / (2 * Cout * Vout * (Vin - Vout))
        """
        if vin <= vout or cout <= 0 or vout <= 0 or l <= 0:
            return 0.0
        return (l * (i_peak_min**2) * vin) / (2.0 * cout * vout * (vin - vout))
