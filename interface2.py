import sys
import math
import threading
import queue
import serial
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtCore import Qt, QTimer

def crc8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc

class AngleWidget(QWidget):
    def __init__(self, send_queue):
        super().__init__()
        self.send_queue = send_queue
        self.current_angle = 0
        self.target_angle = 0
        self.speed = 2  # Velocidade de movimentação do ponteiro
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Layout superior com input e botão
        top_layout = QHBoxLayout()
        self.input_angle = QLineEdit()
        self.input_angle.setPlaceholderText("Ângulo em graus")
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.update_angle)
        top_layout.addWidget(self.input_angle)
        top_layout.addWidget(self.send_button)
        
        # Label do ângulo
        self.angle_label = QLabel("Ângulo atual: 0°")
        self.angle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addLayout(top_layout)
        layout.addWidget(self.angle_label)
        
        self.setLayout(layout)
        self.setFixedSize(300, 400)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_pointer)
        self.timer.start(30)  # Atualização a cada 30ms

    def update_angle(self):
        try:
            angle = int(self.input_angle.text())
            direction = 0x01 if angle >= 0 else 0x00
            abs_angle = abs(angle)
            angle_bytes = abs_angle.to_bytes(2, byteorder='big')
            packet = bytes([0xA0, direction, angle_bytes[0], angle_bytes[1]])
            crc = crc8(packet)
            packet += bytes([crc])
            print("Pacote enviado:", packet.hex().upper())
            self.send_queue.put(packet)  # Envia o pacote para a fila da thread de envio
            self.target_angle = angle  # Mantém o valor negativo, se houver
        except ValueError:
            self.target_angle = self.current_angle  # Se inválido, mantém o atual

    def animate_pointer(self):
        if self.current_angle < self.target_angle:
            self.current_angle += min(self.speed, self.target_angle - self.current_angle)
        elif self.current_angle > self.target_angle:
            self.current_angle -= min(self.speed, self.current_angle - self.target_angle)
        
        self.angle_label.setText(f"Ângulo atual: {self.current_angle}°")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center_x, center_y = 150, 200  # Centro do círculo
        radius = 70
        
        # Desenhar círculo
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawEllipse(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        
        angle_rad = math.radians(-self.current_angle + 90)  # Ajustar para ângulo de relógio
        pointer_x = center_x + radius * math.cos(angle_rad)
        pointer_y = center_y - radius * math.sin(angle_rad)
        
        # Desenhar ponteiro
        painter.setPen(QPen(Qt.GlobalColor.red, 3))
        painter.drawLine(center_x, center_y, int(pointer_x), int(pointer_y))

def send_thread_func(send_queue, port="COM14"):
    try:
        ser = serial.Serial(port, 115200, timeout=1)
    except serial.SerialException as e:
        print(f"Erro ao abrir porta {port}:", e)
        return
    
    while True:
        packet = send_queue.get()
        if packet is None:
            break  # Permite encerrar a thread de forma limpa
        ser.write(packet)
        print(f"Pacote enviado para {port}")
    ser.close()

def receive_thread_func(port):
    try:
        ser = serial.Serial(port, 115200, timeout=1)
    except serial.SerialException as e:
        print("Erro ao abrir porta serial:", e)
        return

    stop_packet = bytes([0xA1, 0x00, 0x00, 0x00, 0x9E])
    last_sent_time = -2 # Start with a negative value to enable sending on startup
    
    while True:
        data = ser.readline()
        if data:
            print(f"Recebido {port}:", data.hex().upper())
        if data == b"1":
            current_time = time.time()
            if current_time - last_sent_time >= 2:  # Check if 2 seconds have passed
                print("Pessoa Detectada")
                send_queue.put(stop_packet)
                last_sent_time = current_time  # Update the last sent time
            
    ser.close()



if __name__ == "__main__":
    send_queue = queue.Queue()
    port_read = "COM1"
    port_write = "COM14"
    
    send_thread = threading.Thread(target=send_thread_func, args=(send_queue, port_write), daemon=True)
    receive_thread = threading.Thread(target=receive_thread_func,args=(port_read),  daemon=True)
    send_thread.start()
    receive_thread.start()
    
    app = QApplication(sys.argv)
    window = AngleWidget(send_queue)
    window.show()
    sys.exit(app.exec())
