import os
import random
import time
import tkinter as tk
import uuid
from tkinter import messagebox

import cv2
import openai
import pygame
from PIL import Image, ImageTk
from gtts import gTTS
from playsound import playsound


def load_interview_questions(filename):
    extracted_texts = []
    script_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_path, filename)

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            extracted_texts = [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        print("질문 파일을 찾을 수 없습니다.")
    return extracted_texts


def create_audio_directory():
    audio_directory = os.path.join(os.getcwd(), "audio")  # 현재 작업 디렉토리 기준의 절대 경로
    if not os.path.exists(audio_directory):
        os.makedirs(audio_directory)
        os.chmod(audio_directory, 0o777)  # 디렉토리에 쓰기 권한 부여


def generate_interview_questions(resume_text):
    prompt = f"Based on the following resume:\n{resume_text}\n\nGenerate interview questions related to the candidate's experience."

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=100
    )

    generated_question = response.choices[0].text.strip()
    return generated_question


def save_interview_questions(filename, questions):
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(questions))


class InterviewApp:
    def __init__(self, root):
        self.root = None
        self.familiar_questions = []
        self.question_frequency = {}  # 질문 빈도수를 저장할 딕셔너리
        self.load_question_frequency()  # 질문 빈도수 불러오기
        self.question_frequency_label = tk.Label(self.root, text="이 질문의 빈도수: 0", font=("Helvetica", 12))
        self.question_frequency_label.pack(pady=5, anchor="nw")
        self.load_familiar_questions()
        self.root = root
        self.root.title("면접 연습 프로그램")
        self.total_start_time = time.time()  # 전체 경과 시간 측정을 위한 시작 시간 기록

        self.current_question_index = 0

        self.question_counter = 0  # 질문 카운터 초기화
        self.question_counter_label = tk.Label(self.root, text="질문 넘김 횟수: 0", font=("Helvetica", 12))
        self.question_counter_label.pack(pady=5, anchor="nw")  # 카운터 레이블을 UI에 추가

        self.add_question_dialog = None  # 대화 상자 인스턴스 변수 초기화
        self.new_question_entry = None  # 질문 입력 필드 인스턴스 변수 초기화

        self.total_timer_label = tk.Label(self.root, text="전체 경과 시간: 00:00:00", font=("Helvetica", 12))
        self.total_timer_label.pack(pady=10, anchor="nw")

        self.question_label = tk.Label(self.root, text="", font=("Helvetica", 16), wraplength=300)
        self.question_label.pack(pady=20)

        self.display_question_button = tk.Button(self.root, text="문장 표시", command=self.display_question)
        self.display_question_button.pack()

        self.next_question_button = tk.Button(self.root, text="다음 문장", command=self.next_question)
        self.next_question_button.pack(pady=10)

        self.generate_question_button = tk.Button(self.root, text="면접 질문 생성", command=self.generate_interview_question)
        self.generate_question_button.pack()

        self.timer_label = tk.Label(self.root, text="", font=("나눔고딕", 12))
        self.timer_label.pack(pady=10)

        self.extracted_texts = load_interview_questions("interview_questions.txt")  # 질문 파일 로드
        self.questions = self.extracted_texts.copy()
        self.current_question_index = 0

        self.add_question_button = tk.Button(self.root, text="질문 추가", command=self.show_add_question_dialog)
        self.add_question_button.pack()

        self.familiar_button = tk.Button(self.root, text="익숙한 질문으로 표시", command=self.mark_as_familiar)
        self.familiar_button.pack(pady=10)

        self.start_time = time.time()
        self.init_time = time.time()  # 문장 표시 초기 시간
        self.is_playing = False  # 음성 재생 여부
        create_audio_directory()  # audio 디렉토리 생성
        pygame.mixer.init()  # mixer 초기화

        self.update_total_timer()  # 전체 경과 시간 업데이트 함수 호출

    def mark_as_familiar(self):
        try:
            print("mark_as_familiar 호출됨")  # 메소드 호출 확인
            if self.current_question_index < len(self.extracted_texts):
                question = self.extracted_texts[self.current_question_index]
                print(f"현재 질문: {question}")  # 현재 질문 출력
                # 익숙한 질문 목록에 현재 질문 추가
                if question not in self.familiar_questions:
                    self.familiar_questions.append(question)
                    print(f"익숙한 질문에 추가됨: {self.familiar_questions}")  # 업데이트된 목록 출력
                    self.save_familiar_questions()
                else:
                    print("이미 목록에 존재하는 질문입니다.")  # 질문이 이미 목록에 있는 경우
            else:
                print("유효한 질문 인덱스가 아닙니다.")  # 현재 질문 인덱스가 유효하지 않은 경우
        except Exception as e:
            print(f"오류 발생: {e}")  # 예외 처리

    def load_familiar_questions(self):
        try:
            with open("familiar_questions.txt", "r", encoding="utf-8") as file:
                self.familiar_questions = [line.strip() for line in file.readlines()]
        except FileNotFoundError:
            pass

    def save_familiar_questions(self):
        with open("familiar_questions.txt", "w", encoding="utf-8") as file:
            for question in self.familiar_questions:
                file.write(question + "\n")

    def show_add_question_dialog(self):
        self.add_question_dialog = tk.Toplevel(self.root)
        self.add_question_dialog.title("질문 추가")
        self.add_question_dialog.geometry("300x100")

        question_label = tk.Label(self.add_question_dialog, text="새로운 질문을 입력하세요:")
        question_label.pack(pady=10)

        self.new_question_entry = tk.Entry(self.add_question_dialog)
        self.new_question_entry.pack()

        confirm_button = tk.Button(self.add_question_dialog, text="추가", command=self.add_question)
        confirm_button.pack(pady=10)

    def display_question(self):

        question = self.extracted_texts[self.current_question_index]
        if question in self.question_frequency:
            self.question_frequency[question] += 1
        else:
            self.question_frequency[question] = 1
        self.save_question_frequency()  # 변경된 질문 빈도수 저장
        self.update_question_frequency_label(question)  # 질문 빈도수 레이블 업데이트

        try:
            if self.current_question_index < len(self.extracted_texts):
                question = self.extracted_texts[self.current_question_index]
                self.question_label.config(text=question)
                self.init_time = time.time()
                if self.is_playing:
                    pygame.mixer.music.stop()
                self.speak_question(question)
                self.update_timer()
                self.start_time = time.time()
        except Exception as e:
            print(f"An error occurred: {e}")

    def update_question_frequency_label(self, question):
        """선택된 질문의 빈도수를 레이블에 업데이트합니다."""
        frequency = self.question_frequency.get(question, 0)
        self.question_frequency_label.config(text=f"이 질문의 빈도수: {frequency}")

    def next_question(self):
        if self.is_playing:
            return

        # '익숙하지 않은 질문' 목록 생성
        unfamiliar_questions = [q for q in self.extracted_texts if q not in self.familiar_questions]

        if unfamiliar_questions:
            # '익숙하지 않은 질문' 목록에서 무작위로 질문 선택
            question = random.choice(unfamiliar_questions)
            self.current_question_index = self.extracted_texts.index(question)
        else:
            # 모든 질문이 '익숙한' 경우, 전체 목록에서 무작위로 질문 선택
            self.current_question_index = random.randint(0, len(self.extracted_texts) - 1)

        # 선택된 질문 표시
        self.display_question()

        # 카운터 업데이트
        self.question_counter += 1
        self.question_counter_label.config(text=f"질문 넘김 횟수: {self.question_counter}")

    def generate_interview_question(self):
        resume_text = """
        이곳에 경력 기술서 텍스트를 입력하세요.
        """

        question = generate_interview_questions(resume_text)
        self.question_label.config(text=question)

    def speak_question(self, question):
        unique_filename = f"question_{uuid.uuid4()}.mp3"
        mp3_path = os.path.join("audio", unique_filename)
        tts = gTTS(text=question, lang='ko', slow=False)
        tts.save(mp3_path)

        # 음성 재생 및 타이머 시작
        playsound(mp3_path)  # 음성 재생
        self.is_playing = False
        self.start_time = time.time()

    def update_timer(self):
        if self.start_time > 0:
            elapsed_time = time.time() - self.init_time
            formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            self.timer_label.config(text=f"경과 시간: {formatted_time}")
        self.root.after(1000, self.update_timer)  # 1초마다 업데이트

    def update_total_timer(self):
        elapsed_time = time.time() - self.total_start_time
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        self.total_timer_label.config(text=f"전체 경과 시간: {formatted_time}")
        self.root.after(1000, self.update_total_timer)  # 1초마다 업데이트

    def add_question(self):
        new_question = self.new_question_entry.get()  # 질문 입력 필드의 내용을 가져옴
        if new_question:
            self.extracted_texts.append(new_question)
            save_interview_questions("interview_questions.txt", self.extracted_texts)
            messagebox.showinfo("알림", "새로운 질문이 추가되었습니다.")
            self.add_question_dialog.destroy()  # 대화 상자

    def load_question_frequency(self):
        try:
            with open("question_frequency.txt", "r", encoding="utf-8") as file:
                for line in file:
                    question, count = line.strip().split(":")
                    self.question_frequency[question] = int(count)
        except FileNotFoundError:
            pass

    def save_question_frequency(self):
        """질문 빈도수를 파일에 저장합니다."""
        with open("question_frequency.txt", "w", encoding="utf-8") as file:
            for question, count in self.question_frequency.items():
                file.write(f"{question}:{count}\n")

    def show_question_frequency(self):
        """질문 빈도수를 보여주는 다이얼로그를 생성합니다."""
        frequency_dialog = tk.Toplevel(self.root)
        frequency_dialog.title("질문 빈도수")
        frequency_dialog.geometry("300x400")
        for question, count in sorted(self.question_frequency.items(), key=lambda item: item[1], reverse=True):
            label = tk.Label(frequency_dialog, text=f"{question}: {count}회")
            label.pack()

    def reset_question_frequency(self):
        """질문 빈도수를 리셋합니다."""
        self.question_frequency = {}
        self.save_question_frequency()
        messagebox.showinfo("알림", "질문 빈도수가 리셋되었습니다.")


class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("카메라 앱")

        self.cap = cv2.VideoCapture(0)  # 웹캠에 접근

        self.label = tk.Label(root)
        self.label.pack()

        self.update_camera()

    def update_camera(self):
        ret, frame = self.cap.read()  # 프레임 읽기
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # BGR to RGB 변환
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
            self.label.config(image=self.photo)
        self.root.after(10, self.update_camera)  # 10ms마다 업데이트


if __name__ == "__main__":
    root = tk.Tk()

    interview_app = InterviewApp(root)
    camera_app = CameraApp(root)

    # 창 크기 설정
    window_width = 1200
    window_height = 1000

    # 화면 중앙에 창 배치
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_position = (screen_width - window_width) // 2
    y_position = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    root.mainloop()
