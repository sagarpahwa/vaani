"""Contract tests for audio serving from the object store."""


def test_audio_served_with_wav_content_type(client, providers):
    providers.store.put("sessions/x/utterances/0.wav", b"RIFFfakewav")
    r = client.get("/audio/sessions/x/utterances/0.wav")
    assert r.status_code == 200
    assert r.content == b"RIFFfakewav"
    assert r.headers["content-type"] == "audio/wav"


def test_audio_missing_key_404(client):
    assert client.get("/audio/sessions/none/missing.wav").status_code == 404
