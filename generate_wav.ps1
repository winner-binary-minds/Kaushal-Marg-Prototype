Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.SetOutputToWaveFile("test_speech.wav")
$speak.Speak("My name is Suresh. I completed 12th standard and I have tailoring experience.")
$speak.Dispose()
Write-Host "Done generating test_speech.wav"
