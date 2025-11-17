# Testing Checklist - Audio Communication System

## ✅ Files Created (All in `test_audio_comunication/`)

- [x] `audio_protocol.py` - FSK modem with error correction
- [x] `microscope_audio_test.py` - Full test suite (6 tests)
- [x] `two_pc_test.py` - Two-computer demo
- [x] `build_standalone.py` - Build .exe for airgapped transfer
- [x] `requirements.txt` - Python dependencies
- [x] `README.md` - Full documentation
- [x] `QUICK_START.md` - Quick guide for testing
- [x] `ARCHITECTURE.md` - System diagrams and technical details
- [x] `CHECKLIST.md` - This file

---

## 📋 Pre-Flight Checklist (Before USB Transfer)

### On THIS Computer (Microfluidics PC)

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run basic test: `python microscope_audio_test.py`
- [ ] Verify all 6 tests pass
- [ ] (Optional) Build .exe: `python build_standalone.py`

### Prepare USB Stick

Copy entire `test_audio_comunication/` folder to USB stick, OR:

**Minimal transfer (if both test PCs have Python):**
- [ ] `audio_protocol.py`
- [ ] `microscope_audio_test.py`
- [ ] `two_pc_test.py`
- [ ] `requirements.txt`
- [ ] `QUICK_START.md`

**Standalone transfer (if test PCs don't have Python):**
- [ ] `dist/microscope_audio_test.exe` (from build_standalone.py)
- [ ] `QUICK_START.md`

---

## 🧪 Test Plan Checklist

### Test Computer 1

- [ ] Copy folder from USB stick
- [ ] Install dependencies (if using Python)
- [ ] Run: `python microscope_audio_test.py`

**Expected Results:**
- [ ] Test 1: System Beep - PASS
- [ ] Test 2: Audio Generation - PASS
- [ ] Test 3: Audio Recording - PASS
- [ ] Test 4: Frequency Detection - PASS
- [ ] Test 5: FSK Protocol - PASS
- [ ] Test 6: Noise Immunity - PASS

**If any fail:** Document which test and error message

---

### Test Computer 2

- [ ] Copy folder from USB stick
- [ ] Install dependencies (if using Python)
- [ ] Run: `python microscope_audio_test.py`

**Expected Results:**
- [ ] All 6 tests pass (same as Computer 1)

**If any fail:** Document which test and error message

---

### Two-Computer Communication Test

**Setup:**
- [ ] Both computers passed individual tests
- [ ] Computers within 1-2 meters of each other
- [ ] Volume at ~60% on both PCs
- [ ] Minimal background noise

**Steps:**

1. [ ] On Computer 2: `python two_pc_test.py receiver`
   - [ ] Shows "Listening for commands..."

2. [ ] On Computer 1: `python two_pc_test.py sender`
   - [ ] Press Enter when prompted

3. [ ] Observe Test 1 (PING/PONG):
   - [ ] Computer 1 sends PING
   - [ ] Computer 2 receives PING
   - [ ] Computer 2 sends PONG
   - [ ] Computer 1 receives PONG
   - [ ] **Result:** PASS / FAIL

4. [ ] Observe Test 2 (CAPTURE/DONE):
   - [ ] Computer 1 sends CAPTURE
   - [ ] Computer 2 receives CAPTURE
   - [ ] Computer 2 simulates capture (3 second delay)
   - [ ] Computer 2 sends DONE
   - [ ] Computer 1 receives DONE
   - [ ] **Result:** PASS / FAIL

---

## 📊 Results Summary

### Computer 1 Individual Tests
- Test 1: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 2: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 3: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 4: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 5: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 6: ⬜ Pass / ⬜ Fail - Notes: ________________

### Computer 2 Individual Tests
- Test 1: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 2: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 3: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 4: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 5: ⬜ Pass / ⬜ Fail - Notes: ________________
- Test 6: ⬜ Pass / ⬜ Fail - Notes: ________________

### Two-Computer Communication
- PING/PONG: ⬜ Pass / ⬜ Fail - Notes: ________________
- CAPTURE/DONE: ⬜ Pass / ⬜ Fail - Notes: ________________

---

## 🎯 Success Criteria

✅ **READY FOR MICROSCOPE DEPLOYMENT** if:
- Both computers pass all 6 individual tests
- Two-computer test passes both PING/PONG and CAPTURE/DONE
- Total transmission time < 5 seconds per command cycle

⚠️ **NEEDS TROUBLESHOOTING** if:
- Individual tests fail → Check audio hardware setup
- Two-computer test fails → Adjust speaker/mic positioning or volume

❌ **CONSIDER ALTERNATIVE** if:
- Cannot get two-computer test to work after troubleshooting
- Background noise too high in production environment
- → Consider optical communication (screen flash + LED)

---

## 🔧 Troubleshooting Guide

### Common Issues and Fixes

**Test 1-2 Fail (No sound output):**
- Check volume is not muted
- Verify speakers/headphones plugged in
- Try: `powershell -c "[console]::beep(1000,500)"`

**Test 3 Fails (No microphone input):**
- Windows Settings → Privacy → Microphone → Allow apps
- Sound settings → Recording devices → Enable microphone
- Check microphone is not muted

**Test 5 Fails (FSK Protocol):**
- This is normal if using built-in laptop speaker/mic (loopback issues)
- Will work fine between two separate computers
- Proceed to two-computer test

**Two-PC Test Fails:**
1. Move computers closer (<1 meter)
2. Increase volume (70-80%)
3. Point speaker directly at microphone
4. Reduce background noise
5. Try different speaker/microphone combination

---

## 📝 Notes Section

**Date Tested:** ________________

**Test Computer 1:**
- Model: ________________
- OS: ________________
- Audio Hardware: ________________

**Test Computer 2:**
- Model: ________________
- OS: ________________
- Audio Hardware: ________________

**Environment:**
- Background noise level: Low / Medium / High
- Distance between computers: _______ meters
- Volume settings: _______ %

**Additional Observations:**
________________________________________________________________
________________________________________________________________
________________________________________________________________

---

## ✨ Next Steps After Successful Testing

- [ ] Report results back (all tests passed!)
- [ ] Document any issues encountered
- [ ] Prepare for microscope PC deployment
- [ ] Build production `microscope_control.exe`
- [ ] Integrate with `run_protocol_cli.py` on microfluidics PC
- [ ] Test on actual microscope setup

---

## 🚀 Production Deployment Checklist (Future)

Once testing is successful, prepare for actual microscope integration:

- [ ] Build `microscope_control.exe` for airgapped microscope PC
- [ ] Test with actual microscope trigger commands
- [ ] Add `microscope.py` controller to microfluidics PC
- [ ] Update `run_protocol_cli.py` to handle `microscope_capture` commands
- [ ] Create YAML config with microscope integration
- [ ] Run full integration test: pump + valve + microscope
- [ ] Document production usage in main README
