from PySide6.QtWidgets import QWidget, QTableWidget, QLabel, QVBoxLayout, QTableWidgetItem, QHeaderView, QMainWindow, QApplication
from PySide6.QtGui import QImage, QPixmap, QPainter, QPainterPath
from PySide6.QtCore import Qt, QRect, QSize
import cv2
import os
import sys

class VideoThumbnailWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)  # Set number of columns
        self.setShowGrid(False)  # Hide grid lines
        self.setEditTriggers(QTableWidget.NoEditTriggers)  # Make cells read-only
        self.horizontalHeader().setVisible(False)  # Hide headers
        self.verticalHeader().setVisible(False)
        
        # Set column widths to be equal
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Enable selection
        self.setSelectionBehavior(QTableWidget.SelectItems)
        self.setSelectionMode(QTableWidget.SingleSelection)
        
        # Connect the itemClicked signal to the slot
        self.cellClicked.connect(self.on_item_clicked)

        self.current_widget = None
        
        # Style
        self.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
            }
            QTableWidget::item {
                padding: 1px;
                border: 2px solid transparent;
                border-radius: 5px;
            }
            QTableWidget::item:selected {
                background-color: rgb(0, 255, 0);
                border: 2px solid rgb(0, 255, 0);
                border-radius: 5px;
            }
        """)

    def add_video(self, video_path):
        """Add a single video thumbnail by providing its path"""
        if not os.path.exists(video_path):
            print(f"Error: Video file not found at {video_path}")
            return

        # Calculate row and column position
        total_items = self.rowCount() * self.columnCount()
        current_col = total_items % self.columnCount()
        current_row = total_items // self.columnCount()
        
        # Add new row if needed
        if current_col == 0:
            self.insertRow(current_row)

        # Create thumbnail
        thumbnail = self.create_video_thumbnail(video_path)
        if thumbnail:
            # Apply rounded corners
            rounded_thumbnail = self.create_rounded_thumbnail(thumbnail)
            
            # Create container widget
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setAlignment(Qt.AlignCenter)
            
            # Create label for thumbnail
            thumb_label = QLabel()
            thumb_label.setPixmap(rounded_thumbnail)
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.setStyleSheet("""
                QLabel {
                    padding: 30px;
                }
            """)
            
            # Create label for video name
            name_label = QLabel(os.path.basename(video_path))
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("color: white;")
            
            # Add widgets to container
            container_layout.addWidget(thumb_label)
            container_layout.addWidget(name_label)
            
            # Set cell widget
            # self.setItem(current_row, current_col, QTableWidgetItem(os.path.basename(video_path)))
            self.setCellWidget(current_row, current_col, container)
            
            # Adjust row height
            self.resizeRowToContents(current_row)

    def on_item_clicked(self, row, col):
        # widget = self.cellWidget(row, col)
        # # Find the QLabel containing the thumbnail
        # thumb_label = widget.findChild(QLabel)
        # if thumb_label:
        #     if self.current_widget: 
        #         self.current_widget.setStyleSheet("")
        #     self.current_widget = thumb_label
        #     thumb_label.setStyleSheet("""
        #         QLabel {
        #             background-color: rgb(0, 255, 0);
        #             padding-bottom: 5px;
        #         }
        #     """)
        # # print(f"Selected video at row {row}, column {col}")
        self.resizeRowsToContents()
        

    def create_rounded_thumbnail(self, pixmap, radius=5):
        """Create a rounded corner version of the thumbnail"""
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRect(0, 0, pixmap.width(), pixmap.height()), radius, radius)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        return rounded

    def clear_thumbnails(self):
        """Clear all thumbnails from the table"""
        self.setRowCount(0)

    def create_video_thumbnail(self, video_path, max_size=120):
        try:
            # Open video file
            cap = cv2.VideoCapture(video_path)
            
            # Read first frame
            ret, frame = cap.read()
            if not ret:
                return None
            
            # Get video dimensions
            height, width = frame.shape[:2]
            
            # Calculate aspect ratio
            aspect_ratio = width / height
            
            # Calculate new dimensions maintaining aspect ratio
            if width > height:
                new_width = max_size
                new_height = int(max_size / aspect_ratio)
            else:
                new_height = max_size
                new_width = int(max_size * aspect_ratio)
            
            # Resize frame
            frame = cv2.resize(frame, (new_width, new_height))
            
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to QImage
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Convert to QPixmap
            pixmap = QPixmap.fromImage(q_img)
            
            # Release video capture
            cap.release()
            
            return pixmap
            
        except Exception as e:
            print(f"Error creating thumbnail: {str(e)}")
            return None


class TextDisplayWidget(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(1)  # Set number of columns for text display
        self.setShowGrid(True)  # Show grid lines
        self.setEditTriggers(QTableWidget.NoEditTriggers)  # Make cells read-only
        self.horizontalHeader().setVisible(False)  # Hide headers
        self.verticalHeader().setVisible(False)

        # Enable selection
        self.setSelectionBehavior(QTableWidget.SelectItems)
        self.setSelectionMode(QTableWidget.SingleSelection)

        # Connect the itemClicked signal to the slot
        self.itemClicked.connect(self.on_item_clicked)

        self.insertRow(0)

        # Style
        self.setStyleSheet("""
            QTableWidget {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
            }
            QTableWidget::item {
                padding: 10px;
            }
        """)

    def add_text(self, text):
        """Add a single text item to the table"""
        # row_position = self.rowCount()
        column_position = self.columnCount() - 1
        print(self.columnCount())
        print(column_position)
        self.insertColumn(column_position)
        print(self.rowCount())
        self.setItem(0, column_position, QTableWidgetItem(text))

    def on_item_clicked(self, item):
        """Handle item click event"""
        row = item.row()
        print(item)
        print(f"Selected text at row {row}: {item.text()}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up the main widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Create and add VideoThumbnailWidget
        self.video_widget = VideoThumbnailWidget()
        layout.addWidget(self.video_widget)

        # Create and add TextDisplayWidget
        self.text_widget = TextDisplayWidget()
        layout.addWidget(self.text_widget)

        # Add some example text to the TextDisplayWidget
        for i in range(5):
            self.text_widget.add_text(f"Text Item {i + 1}")

        # Set the layout for the central widget and make it the main widget
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Example of adding videos (replace with your video paths)
        self.video_widget.add_video("/Volumes/T7/Handball/Videos/Handschuhsheim/TSV vs Hockenheim.mp4")
        self.video_widget.add_video("/Volumes/T7/Handball/Videos/Handschuhsheim/TSV vs. Dossenheim.mp4")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle("Video and Text Display")
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())