import calendar

def analyze_barcode(barcode_receive):
    print(barcode_receive)
#1
    gtin = barcode_receive[2:16]
    fnc1 = " "
    date_length = 6
    start = 0
    ref = 'other'
    search_fnc1 = barcode_receive.find(fnc1)
    check1,check2,check3,check4,check5,check6=0,0,0,0,0,0
    # print("gtin:",gtin)
    if search_fnc1 != -1: #roche
        check1 = barcode_receive[16:18]
        start = 18
        #2
        # print(check1)
        if check1=='10': #Lot
            fnc = barcode_receive.find(fnc1,start)
            lot = barcode_receive[start:fnc]
            check2 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("lot:",lot)
        elif check1=='17': #exp
            exp = barcode_receive[start:start+date_length]
            check2 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("exp.date:",exp)
        elif check1=='11': #pd
            pd = barcode_receive[start:start+date_length]
            check2 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("pd.date:",pd)
        elif check1=='24': #ref
            start = start+1
            fnc = barcode_receive.find(fnc1,start)
            ref = barcode_receive[start:fnc]
            check2 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("ref:",ref)
        elif check1=='21': #serial
            fnc = barcode_receive.find(fnc1,start)
            serial = barcode_receive[start:fnc]
            check2 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("serial:",serial)
        else:
            fnc = barcode_receive.find(fnc1,start)
            if fnc !=-1:
                check2 = barcode_receive[fnc+1:fnc+3]
                start = fnc+3
            else:
                False
        #3
        # print(check2)
        if check2=='10': #Lot
            fnc = barcode_receive.find(fnc1,start)
            lot = barcode_receive[start:fnc]
            check3 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("lot:",lot)
        elif check2=='17': #exp
            exp = barcode_receive[start:start+date_length]
            check3 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("exp.date:",exp)
        elif check2=='11': #pd
            pd = barcode_receive[start:start+date_length]
            check3 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("pd.date:",pd)
        elif check2=='24': #ref
            start = start+1
            fnc = barcode_receive.find(fnc1,start)
            ref = barcode_receive[start:fnc]
            check3 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("ref:",ref)
        elif check2=='21': #serial
            fnc = barcode_receive.find(fnc1,start)
            serial = barcode_receive[start:fnc]
            check3 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("serial:",serial)
        else:
            fnc = barcode_receive.find(fnc1,start)
            if fnc !=-1:
                check3 = barcode_receive[fnc+1:fnc+3]
                start = fnc+3
            else:
                False
        #4
        # print(check3)
        if check3=='10': #Lot
            fnc = barcode_receive.find(fnc1,start)
            lot = barcode_receive[start:fnc]
            check4 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("lot:",lot)
        elif check3=='17': #exp
            exp = barcode_receive[start:start+date_length]
            check4 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("exp.date:",exp)
        elif check3=='11': #pd
            pd = barcode_receive[start:start+date_length]
            check4 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("pd.date:",pd)
        elif check3=='24': #ref
            start = start+1
            fnc = barcode_receive.find(fnc1,start)
            ref = barcode_receive[start:fnc]
            check4 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("ref:",ref)
        elif check3=='21': #serial
            fnc = barcode_receive.find(fnc1,start)
            serial = barcode_receive[start:fnc]
            check4 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("serial:",serial)
        else:
            fnc = barcode_receive.find(fnc1,start)
            if fnc !=-1:
                check4 = barcode_receive[fnc+1:fnc+3]
                start = fnc+3
            else:
                False
        #5
        # print(check4)
        if check4=='10': #Lot
            fnc = barcode_receive.find(fnc1,start)
            lot = barcode_receive[start:fnc]
            check5 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("lot:",lot)
        elif check4=='17': #exp
            exp = barcode_receive[start:start+date_length]
            check5 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("exp.date:",exp)
        elif check4=='11': #pd
            pd = barcode_receive[start:start+date_length]
            check5 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("pd.date:",pd)
        elif check4=='24': #ref
            start = start+1
            fnc = barcode_receive.find(fnc1,start)
            ref = barcode_receive[start:fnc]
            check5 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("ref:",ref)
        elif check4=='21': #serial
            fnc = barcode_receive.find(fnc1,start)
            serial = barcode_receive[start:fnc]
            check5 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("serial:",serial)
        else:
            fnc = barcode_receive.find(fnc1,start)
            if fnc !=-1:
                check5 = barcode_receive[fnc+1:fnc+3]
                start = fnc+3
            else:
                False
                
             
        # print(check5)
        if check5=='10': #Lot
            fnc = barcode_receive.find(fnc1,start)
            lot = barcode_receive[start:fnc]
            check6 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("lot:",lot)
        elif check5=='17': #exp
            exp = barcode_receive[start:start+date_length]
            check6 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("exp.date:",exp)
        elif check5=='11': #pd
            pd = barcode_receive[start:start+date_length]
            check6 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("pd.date:",pd)
        elif check5=='24': #ref
            start = start+1
            fnc = barcode_receive.find(fnc1,start)
            ref = barcode_receive[start:fnc]
            check6 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("ref:",ref)
        elif check5=='21': #serial
            fnc = barcode_receive.find(fnc1,start)
            serial = barcode_receive[start:fnc]
            check6 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("serial:",serial)
        else:
            fnc = barcode_receive.find(fnc1,start)
            if fnc !=-1:
                check6 = barcode_receive[fnc+1:fnc+3]
                start = fnc+3
            else:
                False
        
        # print(check6)
        if check6=='10': #Lot
            fnc = barcode_receive.find(fnc1,start)
            lot = barcode_receive[start:fnc]
            # check6 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("lot:",lot)
        elif check6=='17': #exp
            exp = barcode_receive[start:start+date_length]
            # check6 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("exp.date:",exp)
        elif check6=='11': #pd
            pd = barcode_receive[start:start+date_length]
            # check6 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("pd.date:",pd)
        elif check6=='24': #ref
            start = start+1
            fnc = barcode_receive.find(fnc1,start)
            ref = barcode_receive[start:fnc]
            # check6 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("ref:",ref)
        elif check6=='21': #serial
            fnc = barcode_receive.find(fnc1,start)
            serial = barcode_receive[start:fnc]
            # check6 = barcode_receive[fnc+1:fnc+3]
            start = fnc+3
            # print("serial:",serial)
        else:
            fnc = barcode_receive.find(fnc1,start)
            if fnc !=-1:
                # check6 = barcode_receive[fnc+1:fnc+3]
                start = fnc+3
            else:
                False
    else:
        check1 = barcode_receive[16:18]
        start = 18
        
        # print('ref:',ref)
        # print(check1)
        if check1=='17': #exp
            exp = barcode_receive[start:start+date_length]
            check2 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("exp.date:",exp)
        elif check1=='11': #pd
            pd = barcode_receive[start:start+date_length]
            check2 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("pd.date:",pd)
        
        else:
            False
        # print(check2)
        if check2=='17': #exp
            exp = barcode_receive[start:start+date_length]
            check3 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("exp.date:",exp)
        elif check2=='11': #pd
            pd = barcode_receive[start:start+date_length]
            check3 = barcode_receive[date_length+start:date_length+start+2]
            start = start+date_length+2
            # print("pd.date:",pd)
        elif check2=='10': #lot
            lot = barcode_receive[start:]
            # print("lot:",lot)
        else:
            False

        if check3=='10': #exp
            lot = barcode_receive[start:]
            # print("lot:",lot)
        
        else:
            False
    if exp[4:6]=="00":
        year = int("20" + exp[:2])  # "20"를 추가하여 연도를 만듭니다.
        month = int(exp[2:4]) or 1  # 00 대신 01로 파싱하고, 월이 0일 경우 1로 설정합니다.
        cal=calendar.monthrange(year,month)
        day= cal[1]
        day=str(day)
        exp=exp[0:4]+day
        print("gtin:",gtin,"Lot",lot,"Exp.Date",exp,"REF",ref)
        print("1")
    else:
        print("gtin:",gtin,"Lot",lot,"Exp.Date",exp,"REF",ref)
        print("2")
    # print("gtin:",gtin,"Lot",lot,"Exp.Date",exp,"REF",ref)
    return ref, lot, exp, gtin
        
    # print("gtin:", gtin, "check1:", check1, "lot:", lot, "check2:", check2)            
    

