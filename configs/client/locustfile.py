from locust import HttpUser, task, between

class ServidorUser(HttpUser):
    wait_time = between(0, 0.1)
    host = "http://192.168.10.10"

    @task
    def pagina_inicial(self):
        self.client.get("/")
