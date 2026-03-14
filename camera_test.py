import cv2
import os
import numpy as np

# --- SETTINGS ---
FOLDER_NAME = "muzzle_scans"
STRICTNESS = 0.7 
PASSMARK = 60  # The new "Sweet Spot"
if not os.path.exists(FOLDER_NAME): os.makedirs(FOLDER_NAME)

sift = cv2.SIFT_create()
bf = cv2.BFMatcher()
cap = cv2.VideoCapture(0)

print(f"--- VET-TECH PRO: TARGET {PASSMARK} ---")

while True:
    ret, frame = cap.read()
    if not ret: break

    # UI: Scanning Box
    cv2.rectangle(frame, (210, 130), (430, 370), (255, 255, 0), 2)
    cv2.putText(frame, "AIM AT MUZZLE", (210, 120), 0, 0.6, (255, 255, 0), 2)
    cv2.imshow('VET-TECH PRO', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):
        roi = frame[130:370, 210:430]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        live_img = cv2.equalizeHist(gray)
        kp1, des1 = sift.detectAndCompute(live_img, None)
        
        best_score = 0
        match_id = ""

        # Check all angles in the database
        for file in os.listdir(FOLDER_NAME):
            if file.endswith(".jpg"):
                saved_img = cv2.imread(os.path.join(FOLDER_NAME, file), 0)
                if saved_img is not None:
                    kp2, des2 = sift.detectAndCompute(saved_img, None)
                    if des1 is not None and des2 is not None:
                        matches = bf.knnMatch(des1, des2, k=2)
                        good = [m for m, n in matches if m.distance < STRICTNESS * n.distance]
                        
                        if len(good) > best_score:
                            best_score = len(good)
                            match_id = file.split('_')[0]

        # THE 60-POINT DECISION
        if best_score >= PASSMARK:
            print(f"🎯 MATCH FOUND: {match_id} (Score: {best_score})")
            cv2.putText(frame, f"VERIFIED: {match_id}", (210, 400), 0, 0.8, (0, 255, 0), 2)
            cv2.imshow('VET-TECH PRO', frame)
            cv2.waitKey(2000)
        else:
            print(f"❌ UNKNOWN (Best Score: {best_score}/{PASSMARK})")
            new_id = input("New Animal ID: ")
            
            # Training 3 angles
            for i in range(1, 4):
                while True:
                    _, f = cap.read()
                    cv2.putText(f, f"ANGLE {i}/3: Press 'C'", (200, 450), 0, 0.7, (0, 255, 255), 2)
                    cv2.rectangle(f, (210, 130), (430, 370), (0, 255, 255), 2)
                    cv2.imshow('VET-TECH PRO', f)
                    if cv2.waitKey(1) & 0xFF == ord('c'):
                        s_roi = f[130:370, 210:430]
                        s_gray = cv2.equalizeHist(cv2.cvtColor(s_roi, cv2.COLOR_BGR2GRAY))
                        cv2.imwrite(f"{FOLDER_NAME}/{new_id}_angle{i}.jpg", s_gray)
                        break
            print(f"✅ {new_id} trained.")

    elif key == ord('q'): break

cap.release()
cv2.destroyAllWindows()