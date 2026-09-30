import base64
import io
import json
import sys
import types
import unittest
from unittest import mock

from vision import InvalidImageInput, parse_chat_messages


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+tmXcAAAAASUVORK5CYII="
)
PNG_URL = "data:image/png;base64," + base64.b64encode(PNG).decode("ascii")


def message_with_image(url=PNG_URL):
    return [{"role": "user", "content": [
        {"type": "text", "text": "Describe this image"},
        {"type": "image_url", "image_url": {"url": url}},
    ]}]


class VisionInputTests(unittest.TestCase):
    def test_openai_image_part_becomes_file_and_prompt_marker(self):
        prompt, images = parse_chat_messages(message_with_image())
        self.assertIn("Describe this image", prompt)
        self.assertIn("[Image 1 attached]", prompt)
        self.assertEqual(images[0].as_file_payload(), {
            "name": "image-1.png", "mimeType": "image/png", "buffer": PNG,
        })

    def test_image_only_request_gets_a_question(self):
        prompt, images = parse_chat_messages([{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": PNG_URL}},
        ]}])
        self.assertIn("Describe the attached image", prompt)
        self.assertEqual(len(images), 1)

    def test_bad_image_is_rejected_instead_of_ignored(self):
        for url in ("https://example.com/photo.png", "data:image/png;base64,%%%", "data:image/jpeg;base64," + base64.b64encode(PNG).decode()):
            with self.subTest(url=url[:35]), self.assertRaises(InvalidImageInput):
                parse_chat_messages(message_with_image(url))

    def test_limit_and_role_are_enforced(self):
        with self.assertRaises(InvalidImageInput):
            parse_chat_messages([{"role": "system", "content": [
                {"type": "image_url", "image_url": {"url": PNG_URL}},
            ]}])
        with self.assertRaises(InvalidImageInput):
            parse_chat_messages([{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": PNG_URL}}
                for _ in range(5)
            ]}])


patchright = types.ModuleType("patchright")
sync_api = types.ModuleType("patchright.sync_api")
sync_api.sync_playwright = lambda: None
with mock.patch.dict(sys.modules, {"patchright": patchright, "patchright.sync_api": sync_api}):
    import server


class FakeInput:
    def __init__(self, accept="image/*", multiple=""):
        self.attributes = {"accept": accept, "multiple": multiple}
        self.files = None

    def get_attribute(self, name):
        return self.attributes.get(name)

    def set_input_files(self, files, timeout):
        self.files = files


class FakeInputs:
    def __init__(self, inputs):
        self.inputs = inputs

    def count(self):
        return len(self.inputs)

    def nth(self, index):
        return self.inputs[index]


class UploadTests(unittest.TestCase):
    def test_worker_uploads_actual_image_bytes(self):
        _, images = parse_chat_messages(message_with_image())
        file_input = FakeInput()
        page = mock.Mock()
        page.locator.return_value = FakeInputs([file_input])
        worker = server.MultiAccountBrowserWorker("unused")
        with mock.patch.object(server.time, "sleep"):
            worker._attach_images(page, images)
        self.assertEqual(file_input.files[0]["buffer"], PNG)
        self.assertEqual(file_input.files[0]["mimeType"], "image/png")

    def test_missing_upload_control_fails(self):
        _, images = parse_chat_messages(message_with_image())
        page = mock.Mock()
        page.locator.return_value = FakeInputs([])
        worker = server.MultiAccountBrowserWorker("unused")
        with self.assertRaisesRegex(RuntimeError, "image was not sent"):
            worker._attach_images(page, images)

    def test_generation_waits_for_new_reply(self):
        previous = {"count": 1, "text": "Previous answer"}
        current = {"count": 2, "text": "New answer"}
        replies = iter([previous, previous, current, current, current])
        page = mock.Mock()
        page.evaluate.side_effect = lambda script: next(replies)
        page.locator.return_value.first.is_visible.return_value = False
        worker = server.MultiAccountBrowserWorker("unused")
        with mock.patch.object(server.time, "sleep"):
            answer = worker._generate_on_page(page, "New question", [])
        self.assertEqual(answer, "New answer")
        page.locator.return_value.first.press.assert_called_once_with("Enter")


class FakeHandler(server.MuseHTTPHandler):
    def __init__(self, request_body):
        self.path = "/v1/chat/completions"
        self.headers = {"Content-Length": str(len(request_body))}
        self.rfile = io.BytesIO(request_body)
        self.wfile = io.BytesIO()
        self.status_code = None

    def send_response(self, code):
        self.status_code = code

    def send_header(self, name, value):
        pass

    def end_headers(self):
        pass


class ChatEndpointTests(unittest.TestCase):
    def test_image_reaches_worker_in_chat_request(self):
        body = json.dumps({"model": "muse-spark-1.3", "messages": message_with_image()}).encode()
        handler = FakeHandler(body)
        worker = mock.Mock()
        worker.generate.return_value = ("A picture", 0)
        with mock.patch.object(server, "worker", worker):
            handler.do_POST()
        self.assertEqual(handler.status_code, 200)
        self.assertEqual(worker.generate.call_args.args[1][0].data, PNG)
        response = json.loads(handler.wfile.getvalue())
        self.assertEqual(response["choices"][0]["message"]["content"], "A picture")
        self.assertNotIn("usage", response)

    def test_invalid_image_returns_400_without_calling_worker(self):
        body = json.dumps({"messages": message_with_image("https://example.com/image.png")}).encode()
        handler = FakeHandler(body)
        worker = mock.Mock()
        with mock.patch.object(server, "worker", worker):
            handler.do_POST()
        self.assertEqual(handler.status_code, 400)
        worker.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
