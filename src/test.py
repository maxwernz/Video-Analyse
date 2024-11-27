from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QTreeView, QPushButton, QLineEdit, QLabel, QWidget
from PySide6.QtGui import QStandardItemModel, QStandardItem

# Custom widget class containing a QLabel and QLineEdit
class InputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set up the layout for InputWidget
        layout = QVBoxLayout()
        
        # Create the label and input line
        self.label = QLabel("Enter your text:")
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Type here...")
        
        # Add widgets to the layout
        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        
        # Set the layout for this widget
        self.setLayout(layout)


# Main window class
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set up the main widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Create the QTreeView and fully expand it
        self.tree_view = QTreeView()
        self.model = QStandardItemModel()
        root_item = self.model.invisibleRootItem()
        
        # Populate the tree with some example items
        for i in range(3):
            parent_item = QStandardItem(f"Item {i}")
            for j in range(3):
                child_item = QStandardItem(f"Child {i}.{j}")
                parent_item.appendRow(child_item)
            root_item.appendRow(parent_item)
        
        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()  # Fully expand the tree view
        
        # Add the tree view to the layout
        layout.addWidget(self.tree_view)
        
        # Create the toggle button
        self.toggle_button = QPushButton("Toggle Input Widget")
        self.toggle_button.clicked.connect(self.toggle_input_widget)
        layout.addWidget(self.toggle_button)
        
        # Initialize the InputWidget but keep it hidden initially
        self.input_widget = InputWidget(self)
        self.input_widget.hide()
        layout.addWidget(self.input_widget)
        
        # Set the layout for the central widget and make it the main widget
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def toggle_input_widget(self):
        # Show or hide the InputWidget based on its current state
        if self.input_widget.isVisible():
            self.input_widget.hide()
        else:
            self.input_widget.show()
            self.input_widget.line_edit.setFocus()  # Focus the text input when shown


app = QApplication([])
window = MainWindow()
window.show()
app.exec()
