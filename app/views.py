import base64

import os

from deepface import DeepFace
from django.shortcuts import render
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.views.decorators import gzip
from app import camera
from app.utils import send_email


# Create your views here.
@gzip.gzip_page
def live_feed(request):
    try:
        cam = camera.VideoCamera()
        return StreamingHttpResponse(camera.gen(cam), content_type="multipart/x-mixed-replace;boundary=frame")
    except Exception as e:
        print(e)


def capture_frame(request):
    cam = camera.VideoCamera()  # Create an instance of the VideoCamera
    frame_without_rectangles = cam.get_detected_faces_frame()  # Get the frame without the rectangles
    
    if frame_without_rectangles:  # If a frame was captured
        base64_frame = base64.b64encode(frame_without_rectangles).decode('utf-8')
        print("Frame captured")
        return HttpResponse(base64_frame, content_type="image/jpeg")

    else:
        # Return an empty response or handle it as needed
        print("No frame captured")
        return HttpResponse(status=204)


def camera_feed(request, *args, **kwargs):
    return render(request, 'camera_feed.html')


def face_recognition(request):
    response_data = []

    frame_data = request.POST.get('frame')

    if frame_data is not None:
        # Step 1: Delete the representations_vgg_face.pkl file
        representations_file_path = "static/criminal/database/representations_vgg_face.pkl"
        if os.path.exists(representations_file_path):
            os.remove(representations_file_path)

        # Step 2: Find the most similar identity
        find_results = DeepFace.find(frame_data,
                                     db_path="static/criminal/database",
                                     enforce_detection=False,
                                     model_name="VGG-Face")

        identity = ""
        response_data.clear()

        for result in find_results:
            try:
                identity = result['identity'][0]
                identity = identity.replace("\\", "/")

                similar_faces = DeepFace.verify(frame_data, identity,
                                                enforce_detection=False,
                                                model_name="VGG-Face")

                with open(identity, 'rb') as image_file:
                    # Base64 encode the image
                    image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

                response_data.append({
                    'verified': bool(similar_faces['verified']),
                    'distance': similar_faces['distance'],
                    'threshold': similar_faces['threshold'],
                    'model': similar_faces['model'],
                    'detector_backend': similar_faces['detector_backend'],
                    'similarity_metric': similar_faces['similarity_metric'],
                    'time': similar_faces['time'],
                    'identity': identity,
                    'criminal_image': image_base64
                })
             
            except:
                print("Something went wrong.")

        send_email(response_data)

        return JsonResponse(response_data, safe=False)

    else:
        return HttpResponse(status=204)