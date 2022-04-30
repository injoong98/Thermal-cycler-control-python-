# 쿨링펜 제어 관련 참고자려 링크 : https://blog.naver.com/cosmosjs/222549963664
# MLX90614 샌서관련 참고자료 링크 : https://blog.naver.com/youseok0/222389919984
# PWM 제어 관련 참고자료 링크 : https://rasino.tistory.com/328

import RPi.GPIO as GPIO
from time import sleep

from smbus2 import SMBus            # I2C 통신 모듈
from mlx90614 import mlx90614       # MLX90614 센서 모듈

import pandas as pd                 # 엑셀파일 저장 모듈
from datetime import datetime       # 날짜 모듈



def saveExcelData() :

    # excel 데이터 저장

    global excelData

    now = datetime.now()    # 현재시각 불러오기
    excelTitle = 'Thermal Cycler Test_' + now.strftime('%Y-%m-%d %H:%M:%S')+'_gain='+gain+'.xlsx'   # 엑셀 제목(날짜 & p제어 게인 표시)

    excelDataForSave = {        # 리스트 형태 선언
        'cycle_count' : excelData[0],
        'step' : excelData[1],
        'goal_temperature' : excelData[2],
        'current_temperature' : excelData[3],
        'pwm_input' : excelData[4],
        'fan_state' : excelData[5],
        'step_time' : excelData[6]
    }
    
    dataFrame = pd.DataFrame(excelDataForSave)      # 데이터 프레임으로 전환
    dataFrame.to_excel(excel_writer=excelTitle)     # 엑셀로 저장


def pushExcelData(a,b,c,d,e,f,g) :

    # excel 데이터 추가

    global excelData

    variableArray = [a,b,c,d,e,f,g]

    for i in range(0,len(variableArray)-1):
        excelData[i].append(variableArray[i])



def printStatusMessage(total_cycle, fan_pinState, mode) :
    
    # 상태메시지 출력

    if mode == 1:
        print("denaturation complete")
    elif mode == 2:
        print("primer annealing complete")
    elif mode == 3:
        print("primer extension complete")
    else:
        print("unexpected mode")
        
    print("current cycle : ", str(total_cycle), "   fan state : ", str(fan_pinState))


def tempControlByPWM(current_temp, goal_temp, pelt_pwm, mode) :
    
    global pwm_value
    global gain

    error = goal_temp - current_temp    # P제어의 error값(목표온도 - 현재온도)

    pwm_value = gain * error

    if pwm_value > 60:      # pwm 상한치
        pwm_value = 60
    elif pwm_value < 0:      # pwm 결과값이 음수일경우 0 입력(= 펠티어 작동 중지) 
        pwm_value = 0

    pelt_pwm.ChangeDutyCycle(pwm_value)

    global step_flag
    global step_time

    # 목표온도 도달 시 step_flag로 표시한 뒤 지속시간 체크
    if current_temp == goal_temp and step_flag == False:
        step_flag = True
    elif step_flag == ture:
        step_time = step_time + 0.01



try:
    goal_temp_array = [94,50,70]

    fan_pinNo = 14      # 펜 pin 번호
    fan_pinState = False    # 펜 작동상태

    pelt_pinNo = 18         # 펠티어모듈 pin 번호
    pelt_pwmOn = 70          # Heating 시 펠티어모듈의 PWM 수치
    pelt_pwmOff = 0          # Cooling 시 펠티어모듈의 PWM 수치

    # GPIO 핀 번호 세팅
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(fan_pinNo, GPIO.OUT)
    GPIO.setup(pelt_pinNo, GPIO.OUT)
    
    pelt_pwm = GPIO.PWM(pelt_pinNo, 100)        # 펠티어모듈 PWM 설정
    pelt_pwm.start(0)           # 초기 펠티어모듈 PWM 0으로 시작
    global pwm_value            # PWM 수치 글로벌 변수로 선언
    global gain                 # P제어 gain 값 글로벌 변수 선언
    gain = 5                    # P제어 gain 값 설정
    pwm_value = 0


    I2C_adress = 0x5A       # I2C Bus의 mlx센서 주소 값
    bus = SMBus(1)          # I2C 버스 설정
    sensor = mlx90614(bus, address=I2C_adress)          # mlx센서 통신 설정
    
    total_cycle = 0         # 총 사이클 진행 수


    global step_time        # 각 스텝별 진행시간
    global step_flag        # 각 스텝 진행중인지 여부
    step_now = 1       # 현재 스텝 [1. denaturation  2. primer annealing  3. primer extension]
    step_time = 0
    step_flag = False




    global excelData
    excelData = [[],[],[],[],[],[],[]]


    while True:

        # print("Ambient Temperature :", sensor.get_ambient())        # 주변온도 출력
        print("Object Temperature :", sensor.get_object_1())        # 대상물체온도 출력

        current_temp = sensor.get_object_1()    # 현재 대상온도 값


        # 30사이클 도달 시 반복문 중단
        if total_cycle == 30:
            saveExcelData()     # 엑셀데이터 저장
            print("thermal cycle complete")
            break


        # PCR단계에 따른 목표온도 설정
        if step_now == 1: # denaturation 단계 -------------------------------

            # 94도 까지 가열
            tempControlByPWM(current_temp, goal_temp_array[step_now-1], pelt_pwm, 'heating')

            # denaturation 완료
            if step_time == 4:  

                # step관련 변수들 초기화 & 다음 step 지정
                step_flag = False
                step_time = 0
                step_now = 2

                # 펜 on 설정
                fan_pinState = True
                GPIO.output(fan_pinNo, fan_pinState)

                # 상태메세지 출력
                printStatusMessage(total_cycle, fan_pinState, 1)

        elif step_now == 2:  #primer annealing 단계 -------------------------

            # 50도 까지 냉각
            tempControlByPWM(current_temp, goal_temp_array[step_now-1], pelt_pwm, 'cooling')

            # primer annealing 완료
            if step_time == 4:  

                # step관련 변수들 초기화 & 다음 step 지정
                step_flag = False
                step_time = 0
                step_now = 3

                # 펜 off 설정
                fan_pinState = False
                GPIO.output(fan_pinNo, fan_pinState)

                # 상태메세지 출력
                printStatusMessage(total_cycle, fan_pinState, 2)

        elif step_now == 3:  # primer extension 단계 ------------------------

            # 70도 까지 가열
            tempControlByPWM(current_temp, goal_temp_array[step_now-1], pelt_pwm, 'heating')

            # primer extension 완료
            if step_time == 8:

                # step관련 변수들 초기화 & 다음 step 지정
                step_flag = False
                step_time = 0
                step_now = 1

                # 펜 off 설정
                fan_pinState = False
                GPIO.output(fan_pinNo, fan_pinState)

                # 상태메세지 출력
                printStatusMessage(total_cycle, fan_pinState, 3)

                # 사이클 수 +1
                total_cycle = total_cycle + 1
        else:
            print("unexpected situation occurs")
        

        pushExcelData(total_cycle,step_now,goal_temp_array[step_now-1],current_temp,pwm_value,fan_pinState,step_time)   # 엑셀에 현재 데이터 입력(현재 사이클 수, 현재 pcr단계, 목표온도, 현재온도, pwm입력값, fan작동상태, 단계유지시간)


        sleep(0.01)      # 반복문 0.01초 주기

except KeyboardInterrupt:
    saveExcelData()     # 엑셀데이터 저장
    print("Exit pressed Ctrl+C")

finally:
    print("CleanUp")
    GPIO.cleanup()
    print("End of program")
