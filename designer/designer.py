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
        return np.multiply(np.multiply(strain, modulus), area)

    def peak_forces(self):
        '''Calculates peak applied load forces.'''

        strain = np.array([self.data['PEAKSTRAIN'][x] for x in ['P', 'Q', 'R']])
        modulus = self.data['MODULUS']['val']
        area = self.member_area('BRACE')

        a = self.si(self.data['A'])
        b = self.si(self.data['B'])

        return -2 * self.member_force(strain, modulus, area) * \
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

    # def dynamic_load(self):
    #     ''''''


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
        # dynamic_loading = self.dynamic_load()
        # dw.write('AC', dynamic_loading)
