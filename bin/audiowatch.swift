// origin: maestro
// maestro_version: v2026.09.10.1
//
// audiowatch — prints one line every time the default input device changes.
// No polling: it registers a CoreAudio listener and waits, costing nothing while idle.
// Usage: audiowatch   (first line is the current device, then one line per change)
//
// Output is tab separated: "start|change<TAB>device id<TAB>device name".
// `bin/listen` reads this to rotate a capture segment when the input device changes.

import CoreAudio
import Foundation

func defaultInputDeviceID() -> AudioDeviceID {
    var deviceID = AudioDeviceID(0)
    var size = UInt32(MemoryLayout<AudioDeviceID>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultInputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    AudioObjectGetPropertyData(
        AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size, &deviceID)
    return deviceID
}

func deviceName(_ id: AudioDeviceID) -> String {
    var name: Unmanaged<CFString>?
    var size = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioObjectPropertyName,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    let status = AudioObjectGetPropertyData(id, &address, 0, nil, &size, &name)
    guard status == noErr, let cf = name?.takeRetainedValue() else { return "sconosciuto" }
    return cf as String
}

func report(_ prefix: String) {
    let id = defaultInputDeviceID()
    print("\(prefix)\t\(id)\t\(deviceName(id))")
    fflush(stdout)
}

report("start")

var address = AudioObjectPropertyAddress(
    mSelector: kAudioHardwarePropertyDefaultInputDevice,
    mScope: kAudioObjectPropertyScopeGlobal,
    mElement: kAudioObjectPropertyElementMain)

let queue = DispatchQueue(label: "audiowatch")
let status = AudioObjectAddPropertyListenerBlock(
    AudioObjectID(kAudioObjectSystemObject), &address, queue
) { _, _ in
    report("change")
}

if status != noErr {
    FileHandle.standardError.write("impossibile registrare il listener: \(status)\n".data(using: .utf8)!)
    exit(1)
}

dispatchMain()
