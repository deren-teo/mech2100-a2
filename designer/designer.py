import melib.library as mlib
import numpy as np

from datareader import DataReader
from datawriter import DataWriter

class Designer:
    ''''''
    def __init__(self, filepath):
        ''''''
        self.data = DataReader.read(filepath=filepath)
        self.fp = filepath

    @staticmethod
    def si(quantity):
        ''''''
        if quantity['unt'] != 'mm':
            return NotImplementedError('Only implemented for mm->m')

        return quantity['val'] / 1000

    def member_area(self, member_type):
        ''''''
        member_type = member_type.upper()

        if not member_type in ['CHORD', 'BRACE']:
            raise ValueError(f'Invalid member type "{member_type}"')

        r = self.si(self.data[f'D{member_type}']) / 2
        t = self.si(self.data[f'T{member_type}'])

        return np.pi * (np.power(r, 2) - np.power(r - t, 2))

    def member_force(self, strain, modulus, area):
        ''''''
        return (strain * modulus) * area

    def peak_forces(self):
        '''Calculates peak applied load forces.'''

        strain = self.data['PEAKSTRAIN']['val']
        modulus = self.data['MODULUS']['val']
        area = self.member_area('BRACE')

        a = self.si(self.data['A'])
        b = self.si(self.data['B'])

        return 2 * self.member_force(strain, modulus, area) * \
            np.cos(np.arctan(a / b))

    def gravity_load(self):
        ''''''
        centx = self.data['A']['val'] * 2.5 # centroid x position, mm
        centy = self.data['B']['val'] * 0.5 # centroid y position, mm

        a = self.si(self.data['A'])
        b = self.si(self.data['B'])
        chord_len = 20 * a
        brace_len = 12 * b + 10 * np.linalg.norm([a, b])
        chord_vol = chord_len * self.member_area('CHORD')
        brace_vol = brace_len * self.member_area('BRACE')
        weight = self.data['DENSITY']['val'] * (chord_vol + brace_vol)

        g = self.data['GRAV']['val']    # acceleration due to gravity, m/s^2
        gforce = -0.5 * weight * g      # weight force, N
        agravx = -2.5 * a * gforce / b
        agravy = gforce
        bgravx = -agravx
        bgravy = 0  # roller support, no vertical reaction

        return np.array([centx, centy, weight, agravx, agravy, bgravx, bgravy])

    def dynamic_reaction(self):
        ''''''
        half_peak_forces = 0.5 * self.peak_forces()

        a = self.si(self.data['A'])
        b = self.si(self.data['B'])

        afx = -5 * a * half_peak_forces / b
        afy = half_peak_forces
        bfx = -afx
        bfy = np.zeros(3) # roller support, no vertical reaction

        return np.array([afx, afy, bfx, bfy])

    def dynamic_load(self):
        ''''''
        ax, ay, bx, _ = self.dynamic_reaction()
        half_peak_forces = 0.5 * self.peak_forces()

        a = self.data['A']['val']
        b = self.data['B']['val']
        theta = np.arctan(b / a)

        ab = -ay
        ac = ax
        bc = half_peak_forces / np.sin(theta)
        bd = bx - bc * np.cos(theta)
        cd = -bc
        ce = np.cos(theta) * (2 * bc) + ac
        de = bc
        df = np.cos(theta) * (2 * cd) + bd
        ef = cd
        eg = np.cos(theta) * (2 * de) + ce
        fg = bc
        fh = np.zeros(3)
        gh = -half_peak_forces

        return np.array([ac, ce, eg, bd, df, fh, ab, bc, cd, de, ef, fg, gh])

    def nominal_stress(self):
        ''''''
        dynamic_loading = self.dynamic_load()
        bd, cd = dynamic_loading[3], dynamic_loading[8]
        df, de = dynamic_loading[4], dynamic_loading[9]
        forces = np.array([bd, cd, df, de])

        chord_areas = np.ones(3) * self.member_area('CHORD')
        brace_areas = np.ones(3) * self.member_area('BRACE')
        areas = np.array([chord_areas, brace_areas, chord_areas, brace_areas])

        return forces / areas

    def k_stress_magnification(self):
        ''''''
        bd = df = 1.5    # k-joint, chords
        cd = de = 1.2    # k-joint, braces
        return np.array([bd, cd, df, de])

    def adjusted_stress(self):
        ''''''
        nominal_stress = self.nominal_stress()
        magnification  = self.k_stress_magnification().reshape(4, 1)
        return nominal_stress * magnification

    def fatigue_life(self):
        ''''''
        stresses = np.abs(self.adjusted_stress() / 10**6)
        tr = self.data['TCHORD']['val'] / self.data['TBRACE']['val']
        joint = 'K' # joint D is a K-joint
        overlap = (self.data['JOINTTYPE']['val'] == 'overlap')

        ec3lives = np.zeros(stresses.shape)

        for (i, j), stress in np.ndenumerate(stresses):
            ec3lives[i, j] = mlib.ec3life(stress, tr, joint, overlap)[0]

        nperhour = self.data['NPERHOUR']['val'] / 8
        lifetimes = np.power(np.sum(nperhour / ec3lives, axis=1), -1)

        return np.min(lifetimes)

    def pin_diameters(self):
        ''''''
        gravity_reaction = self.gravity_load()[3:].reshape(4, 1)
        dynamic_reaction = self.dynamic_reaction()
        pin_loads = gravity_reaction + dynamic_reaction

        fa = 0.5 * np.max(np.linalg.norm(pin_loads[:2, :], axis=0))
        fb = 0.5 * np.max(np.linalg.norm(pin_loads[2:, :], axis=0))

        staticfos = self.data['STATICFOS']['val']
        pinyield  = self.data['PINYIELD']['val'] * 10**6

        adia = np.sqrt(4 * fa * staticfos / (0.5 * np.pi * pinyield))
        bdia = np.sqrt(4 * fb * staticfos / (0.5 * np.pi * pinyield))

        return np.array([adia, bdia])

    def physical_results(self):
        ''''''
        life = self.fatigue_life()
        adia, bdia = self.pin_diameters() * 1000

        return np.array([life, adia, bdia])

    def export(self, overwrite=True):
        ''''''
        if not overwrite:
            raise NotImplementedError('Writing to new file not supported')

        dw = DataWriter(self.fp)

        # Table 2
        peak_forces = self.peak_forces()
        dw.write('PEAKFORCE', peak_forces)

        # Table 4
        gravity_loading = self.gravity_load()
        dw.write('CENTX', gravity_loading.reshape(7, 1))

        # Table 5
        dynamic_loading = self.dynamic_load()
        dw.write('AC', dynamic_loading)

        # Table 6
        dynamic_reaction = self.dynamic_reaction()
        dw.write('AFX', dynamic_reaction)

        # Table 7
        nominal_stress = self.nominal_stress() / 10**6
        dw.write('BD', nominal_stress, table=7)

        # Table 8
        magnification_factors = self.k_stress_magnification()
        dw.write('BD', magnification_factors.reshape(4, 1), table=8)

        # Table 9
        adjusted_stress = self.adjusted_stress() / 10**6
        dw.write('BD', adjusted_stress, table=9)

        # Table 10
        physical_results = self.physical_results()
        dw.write('LIFE', physical_results.reshape(3, 1))

        dw.save()
