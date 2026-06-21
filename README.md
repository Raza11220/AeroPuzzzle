# AeroPuzzle

AeroPuzzle is a real-time gesture-controlled sliding puzzle game built with Computer Vision and MediaPipe hand tracking. Capture an image from your webcam and solve the puzzle using only hand gestures—no mouse or touch input required.

---

# Quick Start

## Install

```bash
pip install aeropuzzle
```

## Run

```bash
python -m aeropuzzle
```

---

# Features

* 🖐️ Gesture-controlled gameplay using hand tracking
* 📷 Create puzzles directly from your webcam feed
* 🎯 Pinch gestures to grab and move puzzle pieces
* ⚡ Smooth cursor movement with adaptive filtering
* 🎨 Modern in-game HUD with timer and status indicators
* 🏆 Victory screen with completion time
* 🚪 Automatically closes after puzzle completion

---

# How to Play

1. Launch the game:

```bash
python -m aeropuzzle
```

2. Allow access to your webcam.

3. Position yourself in front of the camera.

4. Use your hand gestures to capture an image.

5. Solve the sliding puzzle by:

   * Moving your hand to control the cursor
   * Pinching to grab a tile
   * Dragging it into position
   * Releasing to swap tiles

6. Complete the puzzle to view your finishing time.

---

# Installation

## Install from PyPI

```bash
pip install aeropuzzle
```

# Requirements

* Python 3.10+
* Webcam

The following dependencies are installed automatically:

* OpenCV
* MediaPipe
* NumPy
* Pillow

---

# Tech Stack

| Component           | Technology |
| ------------------- | ---------- |
| Language            | Python     |
| Computer Vision     | OpenCV     |
| Hand Tracking       | MediaPipe  |
| Image Processing    | Pillow     |
| Numerical Computing | NumPy      |

---

Install in editable mode:

```bash
pip install -e .
```

Build the package:

```bash
pip install build

python -m build
```

Upload to PyPI:

```bash
pip install twine

python -m twine upload dist/*
```

---

# Project Structure

```
AeroPuzzle/
│
├── aeropuzzle/
│   ├── __init__.py
│   ├── __main__.py
│   └── ...
│
├── pyproject.toml
├── README.md
```

---

# PyPI

Install directly from PyPI:

```bash
pip install aeropuzzle
```

## Author

**Ahmad Raza**

Built to explore Computer Vision, MediaPipe hand tracking, and natural gesture-based interaction through an interactive puzzle game.
# AeroPuzzzle
