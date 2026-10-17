"""RF01 — captura de imagem; RNF02 — câmera indisponível."""

import cv2
import numpy as np
import pytest

from visao_llm.camera import Camera, encode_jpeg, resize_max_side
from visao_llm.errors import CameraError


def test_ct03_camera_inexistente_lanca_camera_error():
    """CT03: índice de webcam inexistente -> CameraError (não derruba o app)."""
    cam = Camera(97)
    with pytest.raises(CameraError, match="Câmera indisponível"):
        cam.open()
    assert not cam.is_open


def test_ct04_arquivo_de_video_inexistente():
    """CT04: fonte de vídeo inexistente -> CameraError."""
    with pytest.raises(CameraError, match="não encontrado"):
        Camera("/nao/existe/video.mp4").open()


def test_ler_sem_abrir_lanca_erro():
    with pytest.raises(CameraError):
        Camera(0).read()


def test_ct05_captura_de_imagem_estatica(imagem_teste):
    """CT05: captura funciona com fonte de imagem (simula webcam em demonstração/testes)."""
    with Camera(str(imagem_teste)) as cam:
        f1 = cam.read()
        f2 = cam.read()
    assert f1.shape == (480, 640, 3)
    assert f1 is not f2  # cada leitura devolve uma cópia


def test_captura_de_video_em_loop(tmp_path):
    caminho = tmp_path / "v.avi"
    escritor = cv2.VideoWriter(str(caminho), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    for i in range(3):
        escritor.write(np.full((48, 64, 3), i * 60, np.uint8))
    escritor.release()
    with Camera(str(caminho)) as cam:
        for _ in range(7):  # mais leituras que frames -> volta ao início
            assert cam.read().shape[:2] == (48, 64)


def test_encode_jpeg_redimensiona(frame):
    grande = cv2.resize(frame, (2560, 1920))
    jpeg = encode_jpeg(grande, max_side=1024)
    assert jpeg[:2] == b"\xff\xd8"  # assinatura JPEG
    decod = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert max(decod.shape[:2]) == 1024


def test_resize_nao_aumenta_imagem_pequena(frame):
    assert resize_max_side(frame, 4000) is frame


def test_encode_jpeg_imagem_vazia():
    with pytest.raises(CameraError):
        encode_jpeg(np.empty((0, 0, 3), np.uint8))
