from PySide6.QtWidgets import QWidget, QTableWidget, QLabel, QVBoxLayout, QTableWidgetItem, QHeaderView
from PySide6.QtGui import QImage, QPixmap, QPainter, QPainterPath
from PySide6.QtCore import Qt, QRect, QSize
import cv2
import os

class VideoThumbnailWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setColumnCount(3)  # Set number of columns
        self.setShowGrid(False)  # Hide grid lines
        self.setEditTriggers(QTableWidget.NoEditTriggers)  # Make cells read-only
        self.horizontalHeader().setVisible(False)  # Hide headers
        self.verticalHeader().setVisible(False)
        
        # Set column widths to be equal
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Style
        self.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
            }
            QTableWidget::item {
                padding: 10px;
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
            
            # Create label for video name
            name_label = QLabel(os.path.basename(video_path))
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("color: white;")
            
            # Add widgets to container
            container_layout.addWidget(thumb_label)
            container_layout.addWidget(name_label)
            
            # Set cell widget
            self.setCellWidget(current_row, current_col, container)
            
            # Adjust row height
            self.resizeRowToContents(current_row)

    def create_rounded_thumbnail(self, pixmap, radius=20):
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

    def create_video_thumbnail(self, video_path, max_size=200):
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

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create and show the widget
    widget = VideoThumbnailWidget()
    widget.setWindowTitle("Video Thumbnail Viewer")
    widget.setStyleSheet("background-color: #2b2b2b;")  # Dark background
    widget.resize(800, 600)
    widget.show()
    
    # Load videos automatically when launched
    widget.add_video("/Volumes/T7/Handball/Videos/Handschuhsheim/TSV vs Hockenheim.mp4")
    widget.add_video("/Volumes/T7/Handball/Videos/Handschuhsheim/TSV vs. S3L.mp4")
    # widget.add_video("path/to/your/video3.mp4")
    
    sys.exit(app.exec())