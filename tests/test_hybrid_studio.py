import unittest
import numpy as np
import cv2
from hybrid_studio.engine import (FACE_OVAL,ALIGN,AlignmentError,composite,build_face_mask)


def synthetic_face(cx=100.,cy=100.,size=50.):
    pts=np.zeros((478,2),np.float32)
    for k,idx in enumerate(FACE_OVAL):
        a=2*np.pi*k/len(FACE_OVAL)
        pts[idx]=(cx+size*.48*np.cos(a),cy+size*.60*np.sin(a))
    for idx,xy in zip(ALIGN,[(-.22,-.12),(.22,-.12),(0,0),(-.14,.18),(.14,.18),(0,.50)]):
        pts[idx]=(cx+size*xy[0],cy+size*xy[1])
    return pts


class HybridStudioTests(unittest.TestCase):
    def test_background_is_unchanged(self):
        orig=np.full((200,200,3),(55,75,105),np.uint8)
        gen=np.full((200,200,3),(190,100,40),np.uint8)
        pts=synthetic_face()
        result,mask,_=composite(orig,gen,original_faces=[pts],generated_faces=[pts])
        self.assertTrue(np.array_equal(result[0,0],gen[0,0]))
        self.assertGreater(mask.max(),.8)
        self.assertTrue(np.array_equal(result[190,190],gen[190,190]))

    def test_geometry_mismatch_fails_closed(self):
        arr=np.zeros((200,200,3),np.uint8)
        with self.assertRaises(AlignmentError):
            composite(arr,arr,original_faces=[synthetic_face(100,100)],
                      generated_faces=[synthetic_face(180,180)])

    def test_aspect_mismatch_fails(self):
        with self.assertRaises(AlignmentError):
            composite(np.zeros((200,200,3),np.uint8),np.zeros((240,400,3),np.uint8),
                      original_faces=[synthetic_face()],generated_faces=[synthetic_face()])

    def test_no_faces_fails(self):
        arr=np.zeros((200,200,3),np.uint8)
        with self.assertRaises(AlignmentError):
            composite(arr,arr,original_faces=[],generated_faces=[])


if __name__=='__main__':unittest.main()
