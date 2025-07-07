from rest_framework.routers import DefaultRouter
from .views import MQTTDeviceViewSet


router = DefaultRouter()
router.register(r'', MQTTDeviceViewSet)

urlpatterns = router.urls
