import xlwings

class DataWriter:
    ''''''
    def __init__(self, filepath):
        ''''''
        self.wb = xlwings.Book(filepath)
        self.sh = self.wb.sheets[0]

    def write(self, quantity, value, qcol='C', vcol='F', exit_condition=200):
        ''''''
        rownum = 8  # quantity names always start on row 8

        # Search for the row with the specified quantity
        while (self.sh.range(f'{qcol}{rownum}').value != quantity):
            if rownum > exit_condition:
                raise ValueError(f'Quantity "{quantity}" not found')
            rownum += 1

        self.sh.range(f'{vcol}{rownum}').value = value
        self.wb.save()
