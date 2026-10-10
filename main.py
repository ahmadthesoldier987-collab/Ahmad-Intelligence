
import sys
import uuid

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from database import (
    initialize_database,
    save_message,
    get_conversations,
    get_messages,
)
from ai_engine import ask_ai


class AhmadIntelligence(QMainWindow):
    def __init__(self):
        super().__init__()

        self.conversation_id = str(uuid.uuid4())
        self.busy = False

        initialize_database()

        self.setWindowTitle("Ahmad Intelligence")
        self.resize(1100, 720)
        self.setMinimumSize(760, 520)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #10141f;
                color: #edf2ff;
                font-family: Segoe UI, Arial;
                font-size: 14px;
            }
            QListWidget {
                background-color: #171d2b;
                border: none;
                border-radius: 10px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 7px;
            }
            QListWidget::item:selected {
                background-color: #304568;
            }
            QPushButton {
                background-color: #29364d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 11px;
            }
            QPushButton:hover {
                background-color: #3a4d6c;
            }
            QPushButton:disabled {
                background-color: #252a35;
                color: #9299a7;
            }
            QLineEdit {
                background-color: #202838;
                border: 1px solid #3a465c;
                border-radius: 12px;
                padding: 14px;
                color: white;
            }
            QTextBrowser {
                background-color: #10141f;
                border: none;
                padding: 14px;
            }
        """)

        self.build_ui()
        self.load_conversations()
        self.show_welcome()

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        sidebar = QVBoxLayout()
        sidebar.setSpacing(12)

        logo = QLabel("🧠 Ahmad Intelligence")
        logo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        sidebar.addWidget(logo)

        new_chat = QPushButton("+ New Chat")
        new_chat.clicked.connect(self.new_chat)
        sidebar.addWidget(new_chat)

        self.history = QListWidget()
        self.history.itemClicked.connect(self.open_conversation)
        sidebar.addWidget(self.history, 1)

        offline_label = QLabel("● Local AI")
        offline_label.setStyleSheet("color: #83d6a2; padding: 8px;")
        sidebar.addWidget(offline_label)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(245)
        layout.addWidget(sidebar_widget)

        main = QVBoxLayout()
        main.setSpacing(12)

        heading = QLabel("Your personal AI assistant")
        heading.setFont(QFont("Arial", 19, QFont.Weight.Bold))
        main.addWidget(heading)

        subtitle = QLabel(
            "Ask questions, explore ideas, and learn — privately on your PC."
        )
        subtitle.setStyleSheet("color: #9daac0;")
        main.addWidget(subtitle)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        main.addWidget(self.chat, 1)

        bottom = QHBoxLayout()

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText(
            "Message Ahmad Intelligence..."
        )
        self.message_input.returnPressed.connect(self.send_message)
        bottom.addWidget(self.message_input, 1)

        self.send_button = QPushButton("Send ➤")
        self.send_button.clicked.connect(self.send_message)
        bottom.addWidget(self.send_button)

        main.addLayout(bottom)

        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #9daac0;")
        main.addWidget(self.status)

        main_widget = QWidget()
        main_widget.setLayout(main)
        layout.addWidget(main_widget, 1)

    def show_welcome(self):
        self.chat.setHtml("""
            <div style="text-align:center; margin-top:100px;">
                <h1 style="color:#a9c8ff;">🧠</h1>
                <h2>Welcome to Ahmad Intelligence</h2>
                <p style="color:#9daac0;">
                    Your personal AI assistant.
                </p>
                <p style="color:#9daac0;">
                    Start a conversation by typing below.
                </p>
            </div>
        """)

    def load_conversations(self):
        self.history.clear()

        for conversation_id, _ in get_conversations():
            messages = get_messages(conversation_id)
            first_user_message = next(
                (content for role, content in messages if role == "user"),
                "New conversation",
            )
            title = first_user_message[:30]
            if len(first_user_message) > 30:
                title += "..."

            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, conversation_id)
            self.history.addItem(item)

    def new_chat(self):
        self.conversation_id = str(uuid.uuid4())
        self.show_welcome()
        self.status.setText("New conversation")
        self.message_input.setFocus()

    def open_conversation(self, item):
        self.conversation_id = item.data(Qt.ItemDataRole.UserRole)
        self.render_conversation()

    def render_conversation(self):
        messages = get_messages(self.conversation_id)
        html = []

        for role, content in messages:
            safe = (
                content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )

            if role == "user":
                html.append(
                    f'<p style="color:#a9c8ff;"><b>You</b><br>{safe}</p>'
                )
            else:
                html.append(
                    f'<p style="color:#edf2ff;"><b>Ahmad Intelligence</b>'
                    f'<br>{safe}</p>'
                )

        self.chat.setHtml("<hr>".join(html))
        self.status.setText("Conversation loaded")

    def send_message(self):
        if self.busy:
            return

        question = self.message_input.text().strip()
        if not question:
            return

        self.message_input.clear()

        save_message(self.conversation_id, "user", question)
        self.render_conversation()
        self.load_conversations()

        messages = [
            {"role": role, "content": content}
            for role, content in get_messages(self.conversation_id)
        ]

        self.busy = True
        self.send_button.setEnabled(False)
        self.status.setText("Thinking...")
        QApplication.processEvents()

        try:
            answer = ask_ai(messages)
            save_message(self.conversation_id, "assistant", answer)
            self.render_conversation()
            self.load_conversations()
            self.status.setText("Ready")
        except Exception as error:
            QMessageBox.warning(
                self,
                "AI connection problem",
                "I couldn't reach the local AI model.\n\n"
                "Check that Ollama is running and the model is installed.\n\n"
                f"Details: {error}",
            )
            self.status.setText("AI unavailable — your question was saved")
        finally:
            self.busy = False
            self.send_button.setEnabled(True)
            self.message_input.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Ahmad Intelligence")

    window = AhmadIntelligence()
    window.show()

    sys.exit(app.exec())
