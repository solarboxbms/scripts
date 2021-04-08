#!/usr/bin/env python3
import base64

CELLS = 13
ERRORS = 50

res = {}

#_d = 'Qki6AxE7ugMTNboDYvq5AzbeuQPT97kD9em5A8/8uQOT0rkDV/G3AwUOuAPBHLgDZV+7AwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAATGwAAAAAAAAAAAAAAAAAAAAAAACc5DAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAATvQMAz1wIAFg6AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKq9bTCllKwFtP7//wAAAAAMsokbAAAAABiqsPr/////AAAAAAAAAAAuAAAAZmMAAAC3oQEgD/oAkAGQAQAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAC27ceRAQAAAAAAAAAmXDoWAAAAAAgzfgEAAAAA//8JAFfxtwMMAAAAZV+7AwAAAAAAAAAA'
d = ''

def decode(_d):
    global d
    d = base64.b64decode(_d)
    print(f'Length: {len(d)}')
    # pop
    def read(q, name):
        global d
        if q <= 0:
            res = int.from_bytes(d[:4], 'little') / 2**(-q)
            print(f'{name}:', ':'.join('{:02x}'.format(c) for c in d[:4]), f'({res})')
            d = d[4:]
        else:
            res = int.from_bytes(d[:int(abs(q/8))], 'little')
            print(f'{name}:', ':'.join('{:02x}'.format(c) for c in d[:int(abs(q/8))]), f'({res})')
            d = d[int(abs(q/8)):]
        return res

    def sread(n, name):
        res = read(n, name)
        if res >= 2**(n-1):
            res -= 2**n
        return res


    
    # negatives and 0 are Q numbers
    # positives are bits
    cells = {
        'Voltages': -24,
        'NumMaxVoltages': 32,
        'NumMinVoltages': 32,
        'Resistances': 32
    }

    vars = {
        'Total_Voltage': -24,
        'Vcapacitor': -24,
        'Switch_Current': -23,
        'Switch_RMS_Current': -23,
        '#Cum_Ah_Charge': 64, #-64, # v.5 | 32 - others
        '#Cum_Ah_Discharge': 64, #-64 # v.5 | 32 - others
        'Last_Ah_Charge': 32,
        'Last_Ah_Discharge': 32,
        'Switch_Temperature': -24,
        'Micro_Temperature': -24,
        'Batt_Temperature_1': -24,
        'Batt_Temperature_2': -24,
        'SOC': 16,
        'SOH': 16, 
        'Status': 8, # bool
        'Errors (all)': 8,
        #'Errors_Generic_Error': 8,
        #'Errors_Current': 8,
        #'Errors_Voltage': 8,
        #'Errors_Temperature': 8,
        #'Errors_Communication': 8,
        #'Errors_Device_Profile': 8,
        #'Errors_Reserved': 8,
        #'Errors_Manufacturer': 8,
        'Switch_On': 8 # bool
    }

    vars_internals = {
        'Times_Main_Interrupt': 32,
        '#First_Update': 16,
        '_Filler2': 16*3+8,
        '#Num_Cell_Charging': 16, # equal to 'AFE_NumCellMax' or 0
        '#Num_Cell_Discharging': 16,
        'AFE_NumCellMin': 16,
        'AFE_Vmin': -24,
        '_Filler3': 16,
        'AFE_NumCellMax': 16,
        'AFE_Vmax': -24,
        'Enable_Discharge': 8, # bool
        'Init_Cell': 16

    }

    # cells
    for kcell, vcell in cells.items():
        for i in range(1, CELLS+1):
            z = read(vcell, f'{kcell}.{i}')
            #print(f'{kcell}[{i}]', z)
            res[f'{kcell}.{i}'] = z

    # info
    for kvar, vvar in vars.items():
        """
        if 'Temp' in kvar:
            #print(kvar, read(vvar)*10)
            res[kvar] = read(vvar)
        else:
            #print(kvar, read(vvar))
        """
        if kvar.startswith('#'):
            res[kvar[1:]] = sread(vvar, kvar[1:])
        else:
            res[kvar] = read(vvar, kvar)

    # errors buffer
    #res['Errors'] = {}
    for i in range(1, ERRORS+1):
        #print(f'Errors[{i}]', read(8))
        res[f'Errors.{i}'] = read(8, f'Errors.{i}')

    #print('NumberOfErrors', read(8))
    res['NumberOfErrors'] = read(8, 'NumberOfErrors') # ?

    # timestamp of errors in buffer
    #res['TimeStamp_Errors'] = {}
    for i in range(1, ERRORS+1):
        #print(f'TimeStamp_Errors[{i}]', read(32))
        res[f'TimeStamp_Errors.{i}'] = read(32, f'TimeStamp_Errors.{i}')
    
    res['_Filler1'] = read(16, '_Filler')

    res['TimesCurrentIntegrated'] = read(32, 'TimesCurrentIntegrated')
    res['IsMaster'] = read(8, 'IsMaster') # ?
    res['Cum_Ah'] = sread(64, 'Cum_Ah')

    # internals info
    for kvar, vvar in vars_internals.items():
        #print(kvar, read(vvar))
        if kvar.startswith('#'):
            res[kvar[1:]] = sread(vvar, kvar[1:])
        else:
            res[kvar] = read(vvar, kvar)

    #print(len(d))
    #print(d)
    print(f'+ more:', ':'.join('{:02x}'.format(c) for c in d))
    return res
