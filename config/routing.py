from django.urls import re_path
from reviews import consumers

websocket_urlpatterns = [
    # ws://localhost:8000/ws/repos/1/reviews/
    # the repo_id tells the consumer which repo to watch
    re_path(r'ws/repos/(?P<repo_id>\d+)/reviews/$', consumers.ReviewConsumer.as_asgi()),
]