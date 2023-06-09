from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from control.camera import Camera
from control.servos import Gimbal

gimbal = Gimbal()

def index(request):
    return render(request, "index.html")

def move(request):
    if 'direction' in request.POST:
        if request.POST['direction'] == 'up':
            gimbal.move_relative((0,5))
        if request.POST['direction'] == 'down':
            gimbal.move_relative((0,-5))
        if request.POST['direction'] == 'left':
            gimbal.move_relative((-5,0))
        if request.POST['direction'] == 'right':
            gimbal.move_relative((5,0))
        if request.POST['direction'] == 'zoom_in':
            Camera().zoom(Camera.ZoomState.ZOOM_IN)
        if request.POST['direction'] == 'zoom_out':
            Camera().zoom(Camera.ZoomState.ZOOM_OUT)
    else:
        print(request.POST)
    return JsonResponse({'t':True})

def gen(cam):
    """Video streaming generator function."""
    while True:
        frame = cam.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def video_feed(request):
    return StreamingHttpResponse(gen(Camera()), content_type="multipart/x-mixed-replace; boundary=frame")
