"""Register the scene using background features, excluding the person and contact area."""
import cv2
import numpy as np


class CameraRegistration:
    def __init__(self, width, height, contact_start):
        self.width, self.height = width, height
        self.contact_start = contact_start
        self.matrix = np.eye(3, dtype=np.float32)
        self.previous = self.previous_mask = None
        self.lost = False
        self.frames = []

    def update(self, gray, alpha):
        mask = cv2.dilate((alpha > .08).astype(np.uint8), np.ones((19, 19), np.uint8))
        if self.contact_start is not None:
            mask[round(self.contact_start * self.height):] = 1
        valid = (1 - mask) * 255
        if self.previous is not None and not self.lost:
            self._register(gray, valid)
        self.previous, self.previous_mask = gray, valid
        self.frames.append(None if self.lost else self.matrix.tolist())
        return None if self.lost else self.matrix

    def _register(self, gray, valid):
        points = cv2.goodFeaturesToTrack(self.previous, 180, .012, 9, mask=self.previous_mask)
        if points is None or len(points) < 8:
            self.lost = True
            return
        forward, status, _ = cv2.calcOpticalFlowPyrLK(self.previous, gray, points, None)
        if forward is None or status is None:
            self.lost = True
            return
        backward, back_status, _ = cv2.calcOpticalFlowPyrLK(gray, self.previous, forward, None)
        if backward is None or back_status is None:
            self.lost = True
            return
        start, end = points[:, 0], forward[:, 0]
        xy = np.rint(end).astype(int)
        x, y = xy[:, 0], xy[:, 1]
        consistent = ((status[:, 0] == 1) & (back_status[:, 0] == 1)
                      & (np.linalg.norm(start - backward[:, 0], axis=1) < 1.2)
                      & (x >= 0) & (x < self.width) & (y >= 0) & (y < self.height))
        consistent &= valid[np.clip(y, 0, self.height-1), np.clip(x, 0, self.width-1)] != 0
        start, end = start[consistent], end[consistent]
        if len(start) < 8:
            self.lost = True
            return
        step, inliers = cv2.estimateAffinePartial2D(start, end, method=cv2.RANSAC, ransacReprojThreshold=1.7)
        if step is None or not np.isfinite(step).all():
            self.lost = True
            return
        accepted = start[inliers[:, 0] != 0]
        scale = np.linalg.norm(step[:, 0])
        self.lost = (len(accepted) < max(8, .60*len(start))
                     or np.ptp(accepted[:, 0]) < .20*self.width
                     or np.ptp(accepted[:, 1]) < .08*self.height
                     or not .94 <= scale <= 1.06
                     or np.linalg.norm(step[:, 2]) > .085*max(self.width,self.height))
        if not self.lost:
            self.matrix = np.vstack([step, [0, 0, 1]]) @ self.matrix

    def contact(self, alpha, matrix):
        if self.contact_start is None or matrix is None:
            return np.zeros_like(alpha)
        ramp = np.clip((np.arange(self.height, dtype=np.float32)/self.height-self.contact_start)/.10, 0, 1)
        plane = np.broadcast_to(ramp[:, None], alpha.shape).copy()
        return cv2.warpAffine(plane, matrix[:2], (self.width,self.height), borderMode=cv2.BORDER_REPLICATE)


def protect_attached_motion(contact, alpha, gray, previous, step):
    """Keep moving regions connected to the subject near the preserved plane."""
    if previous is None or step is None:
        return contact
    height, width = gray.shape
    aligned = cv2.warpAffine(previous, step[:2], (width,height), borderMode=cv2.BORDER_REPLICATE)
    delta = cv2.absdiff(gray, aligned)
    # Localize candidates to the contact boundary to avoid absorbing moving backgrounds.
    candidates = ((delta > 16) & (contact > 0.02) & (contact < .99)).astype(np.uint8)
    candidates = cv2.morphologyEx(candidates, cv2.MORPH_CLOSE, np.ones((7,7),np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidates)
    near = cv2.dilate((alpha > .45).astype(np.uint8), np.ones((13,13),np.uint8))
    connected = np.unique(labels[near != 0])
    keep = np.zeros(count, np.uint8)
    for index in connected:
        if index and 12 <= stats[index, cv2.CC_STAT_AREA] <= .035*width*height:
            keep[index] = 1
    extra = cv2.GaussianBlur(cv2.dilate(keep[labels].astype(np.float32), np.ones((7,7),np.uint8)), (9,9), 2)
    return np.maximum(contact, extra)
