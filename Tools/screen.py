from PIL import ImageGrab


def capture_screen(path="screen.png"):
    img = ImageGrab.grab()
    img.save(path)
    return path
