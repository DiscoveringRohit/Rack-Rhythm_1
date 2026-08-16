import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// TODO: Replace with your actual Firebase project config
const firebaseConfig = {
  apiKey: "AIzaSyC8ObbjHA7ybslVdR14lY6rXHHwtZrGLOY",
  authDomain: "civic-sense-f0f41.firebaseapp.com",
  projectId: "civic-sense-f0f41",
  storageBucket: "civic-sense-f0f41.firebasestorage.app",
  messagingSenderId: "830490915306",
  appId: "1:830490915306:web:e3054414256ecb2becc293",
  measurementId: "G-J6W3956MDG"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);
