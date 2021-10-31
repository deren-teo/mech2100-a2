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
        '''
        Calculates the area of a member based on whether it is a chord
        or brace.
        '''
        member_type = member_type.upper()

        if not member_type in ['CHORD', 'BRACE']:
            raise ValueError(f'Invalid member type "{member_type}"')

        r = self.si(self.data[f'D{member_type}']) / 2
        t = self.si(self.data[f'T{member_type}'])

        return np.pi * (np.power(r, 2) - np.power(r - t, 2))

    def member_force(self, strain, modulus, area):
        '''
        Calculates the force on a member given its strain, elastic
        modulus and area.
        '''
        return (strain * modulus) * area

    def peak_forces(self):
        '''
        Calculates peak applied load forces.

        Assumes that if the member strains are positive, the member must be
        in tension.
        '''

        strain = self.data['PEAKSTRAIN']['val']
        modulus = self.data['MODULUS']['val']
        area = self.member_area('BRACE')

        a = self.si(self.data['A'])
        b = self.si(self.data['B'])

        return 2 * self.member_force(strain, modulus, area) * \
            np.cos(np.arctan(a / b))

    def static_force(self):
        '''
        Calculates the force on the supports exerted by the weight of
        the truss.

        Sign convention: upwards is positive y-direction, left-to-right
        is positive x-direction.
        '''
        centx = self.data['A']['val'] * 2.5 # centroid x position, mm
        centy = self.data['B']['val'] * 0.5 # centroid y position, mm

        a = self.si(self.data['A'])
        b = self.si(self.data['B'])
        chord_len = 20 * a
        brace_len = 12 * b + 10 * np.linalg.norm([a, b])
        chord_vol = chord_len * self.member_area('CHORD')
        brace_vol = brace_len * self.member_area('BRACE')
        mass = self.data['DENSITY']['val'] * (chord_vol + brace_vol)

        g = self.data['GRAV']['val']    # acceleration due to gravity, m/s^2
        wforce = -0.5 * mass * g        # weight force acting on one side, N
        agravx = -2.5 * (a / b) * wforce
        agravy = wforce
        bgravx = -agravx
        bgravy = 0  # roller support, no vertical reaction

        return np.array([centx, centy, mass, agravx, agravy, bgravx, bgravy])

    def static_reaction(self):
        '''
        Calculates the support reactions due to the weight of the truss.

        Sign convention: upwards is positive y-direction, left-to-right
        is positive x-direction.
        '''
        return -self.static_force()

    def dynamic_force(self):
        '''
        Calculates the force on the supports exerted by the load on the truss.

        Sign convention: upwards is positive y-direction, left-to-right
        is positive x-direction.
        '''
        load_force = 0.5 * self.peak_forces() # load force acting on one side

        a = self.si(self.data['A'])
        b = self.si(self.data['B'])

        afx = -5 * (a / b) * load_force
        afy = load_force
        bfx = -afx
        bfy = np.zeros(3) # roller support, no vertical reaction

        return np.array([afx, afy, bfx, bfy])

    def dynamic_reaction(self):
        '''
        Calculates the support reactions due to the load on the truss.

        Sign convention: upwards is positive y-direction, left-to-right
        is positive x-direction.
        '''
        return -self.dynamic_force()

    def dynamic_load(self):
        '''
        Calculates the member forces due to the load on the truss.

        Sign convention: upwards is positive y-direction, left-to-right
        is positive x-direction, tension is positive member force.
        '''
        ax, ay, bx, _ = self.dynamic_reaction()
        load_force = 0.5 * self.peak_forces() # load force acting on one side

        a = self.data['A']['val']
        b = self.data['B']['val']
        alpha = np.arctan(b / a)

        ab = ay
        ac = -ax
        bc = -ab / np.sin(alpha)
        bd = -bx - bc * np.cos(alpha)
        cd = -bc
        ce = ac + 2 * bc * np.cos(alpha)
        de = -cd
        df = bd + 2 * cd * np.cos(alpha)
        ef = -de
        eg = ce + 2 * de * np.cos(alpha)
        fg = -ef
        fh = np.zeros(3)
        gh = -load_force

        return np.array([ac, ce, eg, bd, df, fh, ab, bc, cd, de, ef, fg, gh])

    def nominal_stress(self):
        '''
        Calculates the stress range experienced by chord members due to the
        load on the truss.

        Note that the stress ranges between zero and the peak stress, so the
        stress range is simple the magnitude of the peak stress.
        '''
        dynamic_loading = self.dynamic_load()
        bd, cd = dynamic_loading[3], dynamic_loading[8]
        df, de = dynamic_loading[4], dynamic_loading[9]
        forces = np.array([bd, cd, df, de])

        chord_areas = np.ones(3) * self.member_area('CHORD')
        brace_areas = np.ones(3) * self.member_area('BRACE')
        areas = np.array([chord_areas, brace_areas, chord_areas, brace_areas])

        return np.abs(forces / areas)

    def k_stress_magnification(self):
        '''
        Determines the correct stress magnification factors for the each of
        the members in the specified joint.
        '''
        bd = df = 1.5    # all chords
        cd = de = 1.2    # k-joint braces
        return np.array([bd, cd, df, de])

    def adjusted_stress(self):
        '''
        Calculates the adjusted stress range experienced by chord members
        due to the load on the truss, adjusted by appropriate
        magnification factors.

        Note that the stress ranges between zero and the peak stress, so the
        stress range is simple the magnitude of the peak stress.
        '''
        nominal_stress = self.nominal_stress()
        magnification  = self.k_stress_magnification().reshape(4, 1)
        return nominal_stress * magnification

    def fatigue_life(self):
        '''
        Calculates the expected life in hours of the truss according
        to EuroCode 3.
        '''
        stresses = self.adjusted_stress() / 10**6
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
        '''
        Calculates the minimum pin diamters of the supports.
        '''
        static_reaction = self.static_reaction()[3:].reshape(4, 1)
        dynamic_reaction = self.dynamic_reaction()
        pin_loads = static_reaction + dynamic_reaction

        fa = 0.5 * np.max(np.linalg.norm(pin_loads[:2, :], axis=0))
        fb = 0.5 * np.max(np.linalg.norm(pin_loads[2:, :], axis=0))

        staticfos = self.data['STATICFOS']['val']
        pinyield  = self.data['PINYIELD']['val'] * 10**6

        adia = np.sqrt(4 * fa * staticfos / (0.5 * np.pi * pinyield))
        bdia = np.sqrt(4 * fb * staticfos / (0.5 * np.pi * pinyield))

        return np.array([adia, bdia])

    def physical_results(self):
        '''
        Calculates a number of physical results for the truss. (I.e. expected
        life in hours and minimum clevis-pin support pin diameters.)
        '''
        life = self.fatigue_life()
        adia, bdia = self.pin_diameters() * 1000

        return np.array([life, adia, bdia])

    def export(self, overwrite=True):
        '''
        Writes the calculations to given Excel file.
        '''
        if not overwrite:
            raise NotImplementedError('Writing to new file not supported')

        dw = DataWriter(self.fp)

        # Table 2
        peak_forces = self.peak_forces()
        dw.write('PEAKFORCE', peak_forces)

        # Table 4
        static_force = self.static_force()
        dw.write('CENTX', static_force.reshape(7, 1))

        # Table 5
        dynamic_loading = self.dynamic_load()
        dw.write('AC', dynamic_loading)

        # Table 6
        dynamic_force = self.dynamic_force()
        dw.write('AFX', dynamic_force)

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
