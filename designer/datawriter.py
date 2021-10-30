import xlwings

class DataWriter:
    ''''''
    def __init__(self, filepath, exit_condition=200):
        ''''''
        self.wb = xlwings.Book(filepath)
        self.sh = self.wb.sheets[0]
        self.exit_condition = exit_condition

    # TODO: make this write per table
    def write(self, quantity, value, table=0, qcol='C', vcol='F', tcol='D'):
        ''''''
        rownum = 8  # quantity names always start on row 8

        # Specify a table to skip to
        if table:
            while (self.sh.range(f'{tcol}{rownum}').value != table):
                rownum += 1

        # Search for the row with the specified quantity
        while (self.sh.range(f'{qcol}{rownum}').value != quantity):
            if rownum > self.exit_condition:
                raise ValueError(f'Quantity "{quantity}" not found')
            rownum += 1

        self.sh.range(f'{vcol}{rownum}').value = value

    def save(self):
        ''''''
        self.wb.save()
