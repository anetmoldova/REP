from django.test import Client

# Create your tests here.


def test_landing_page():
    client = Client()
    response = client.get('/')
    assert response.status_code == 200
