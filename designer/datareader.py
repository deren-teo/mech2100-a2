import numpy as np
# import xlwings

class DataReader:
    ''''''
    def __init__(self, filepath):
        ''''''
        # self.wb = xlwings.Book(filepath)
        # self.sh = self.wb.sheets[0]

    @classmethod
    def read(cls, filepath):
        ''''''
        # TODO: do this properly
        data = {
            'A': {'unt': 'mm', 'val': 1200},
            'B': {'unt': 'mm', 'val': 2000},
            'DCHORD': {'unt': 'mm', 'val': 139.7},
            'TCHORD': {'unt': 'mm', 'val': 5.4},
            'DBRACE': {'unt': 'mm', 'val': 60.3},
            'TBRACE': {'unt': 'mm', 'val': 3.6},
            'JOINT': {'unt': 'na', 'val': 'D'},
            'JOINTTYPE': {'unt': 'na', 'val': 'overlap'},
            'SG': {'unt': 'na', 'val': 'DE'},
            'PEAKSTRAIN': {'unt': 'uul', 'val': np.array([145, 195, 590])},
            'NPERHOUR': {'unt': 'ul', 'val': np.array([200, 420, 120])},
            'GRAV': {'unt': 'm/s2', 'val': 9.81},
            'MODULUS': {'unt': 'MPa', 'val': 207000},
            'DENSITY': {'unt': 'kg/m3', 'val': 7850},
            'POISSON': {'unt': 'ul', 'val': 0.3},
            'CHSYIELD': {'unt': 'MPa', 'val': 350},
            'PINYIELD': {'unt': 'MPa', 'val': 350},
            'STATICFOS': {'unt': 'ul', 'val': 1.5},
            'CODE': {'unt': 'na', 'val': 'Eurocode 3'},
        }

        return data
