import serial
import time

def serial_bridge(input_port: str, output_port: str, baudrate: int = 115200):
    data_out = bytes.fromhex("FF 00 00 00 FF")
    try:
        ser_in = serial.Serial(input_port, baudrate, timeout=1)
        ser_out = serial.Serial(output_port, baudrate, timeout=1)
        print(f"Listening on {input_port} and writing to {output_port}")
        
        while True:
            if ser_in.in_waiting > 0:
                data_in = ser_in.read(ser_in.in_waiting)
                print(f"Received: {data_in}")
                if data_in == b"1":
                    ser_out.write(data_out)
                    print(f"Sent: {data_out}")
                    time.sleep(1) # Send data one time and wait till the sensor "tick down"
            time.sleep(0.05)  # Prevents excessive CPU usage
    
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ser_in.close()
        ser_out.close()

if __name__ == "__main__":
    input_port = "COM1"  # Change to your input serial port
    output_port = "COM3"  # Change to your output serial port
    serial_bridge(input_port, output_port)
