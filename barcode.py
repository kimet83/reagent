from flask import jsonify

def analyze_barcode(type_receive, barcode_receive):
    try:
        gtin = barcode_receive[2:16]
        ref, lot, exp = 'other', '0', '0'

        check1 = barcode_receive[16:18]
        check2 = barcode_receive[26:28]
        check3 = barcode_receive[24:26]
        check4 = barcode_receive[38:40]
        check5 = barcode_receive[47:49]

        if type_receive == 'roche':
            if check1 == '10':
                lot = barcode_receive[18:24]
                if check2 == '17':
                    ref = barcode_receive[37:48]
                    exp = barcode_receive[28:34]
                elif check2 == '11':
                    ref = barcode_receive[45:56]
                    exp = barcode_receive[36:42]
                else:
                    raise Exception('불일치 바코드!')
            elif check1 == '11':
                if check3 == '17':
                    ref = barcode_receive[35:46]
                    lot = barcode_receive[61:69]
                    exp = barcode_receive[26:32]
                elif check3 == '24':
                    if check4 == '10':
                        ref = barcode_receive[27:38]
                        lot = barcode_receive[40:48]
                        exp = barcode_receive[50:56]
                    elif check5 == '10':
                        ref = barcode_receive[27:38]
                        lot = barcode_receive[49:57]
                        exp = barcode_receive[59:65]
                    else:
                        raise Exception('불일치 바코드!')
                else:
                    raise Exception('불일치 바코드!')
            else:
                raise Exception('불일치 바코드!')
        elif type_receive == 'open':
            if check1 == '10':
                lot = barcode_receive[18:22]
                if barcode_receive[22:24] == '17':
                    exp = barcode_receive[24:30]
                else:
                    raise Exception('불일치 바코드!')
            elif check1 == '11':
                if barcode_receive[24:26] == '17':
                    exp = barcode_receive[26:32]
                    lot = barcode_receive[34:]
                else:
                    raise Exception('불일치 바코드!')
            elif check1 == '17':
                exp = barcode_receive[18:24]
                if check3 == '10':
                    lot = barcode_receive[26:]
                else:
                    raise Exception('불일치 바코드!')
        return ref, lot, exp, gtin
    except Exception as e:
        return jsonify({'msg': str(e)})
