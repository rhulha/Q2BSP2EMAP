"""Tiny vector/plane math used to rebuild brush polygons from BSP planes."""
from __future__ import annotations

import math

from .config import EPSILON


class _V:
    __slots__ = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float):
        self.x = x; self.y = y; self.z = z

    def dot(self, o: "_V") -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "_V") -> "_V":
        return _V(self.y * o.z - self.z * o.y,
                  self.z * o.x - self.x * o.z,
                  self.x * o.y - self.y * o.x)

    def plus(self, o: "_V") -> "_V":
        return _V(self.x + o.x, self.y + o.y, self.z + o.z)

    def minus(self, o: "_V") -> "_V":
        return _V(self.x - o.x, self.y - o.y, self.z - o.z)

    def times(self, s: float) -> "_V":
        return _V(self.x * s, self.y * s, self.z * s)

    def divided_by(self, s: float) -> "_V":
        return _V(self.x / s, self.y / s, self.z / s)

    def normalize(self) -> "_V":
        l = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        return _V(self.x / l, self.y / l, self.z / l) if l > 0 else _V(0.0, 0.0, 0.0)


class _Plane:
    def __init__(self, nx: float, ny: float, nz: float, bsp_dist: float):
        self.normal = _V(nx, ny, nz)
        self.distance = -bsp_dist  # convention: distance_to_point = n·p + distance

    def distance_to_point(self, p: _V) -> float:
        return self.normal.dot(p) + self.distance


def _intersect_3(a: _Plane, b: _Plane, c: _Plane) -> _V | None:
    denom = a.normal.dot(b.normal.cross(c.normal))
    if abs(denom) < EPSILON:
        return None
    t1 = b.normal.cross(c.normal).times(-a.distance)
    t2 = c.normal.cross(a.normal).times(b.distance)
    t3 = a.normal.cross(b.normal).times(c.distance)
    return t1.minus(t2).minus(t3).divided_by(denom)


def _compute_polys(planes: list[_Plane]) -> list[list[_V]]:
    n = len(planes)
    polys: list[list[_V]] = [[] for _ in range(n)]
    for i in range(n - 2):
        for j in range(i + 1, n - 1):
            for k in range(j + 1, n):
                v = _intersect_3(planes[i], planes[j], planes[k])
                if v is None:
                    continue
                if all(pl.distance_to_point(v) <= EPSILON for pl in planes):
                    polys[i].append(v)
                    polys[j].append(v)
                    polys[k].append(v)
    _sort_polys(polys, planes)
    return polys


def _sort_polys(polys: list[list[_V]], planes: list[_Plane]) -> None:
    for n_idx, polygon in enumerate(polys):
        if len(polygon) < 3:
            continue
        plane = planes[n_idx]
        cx = sum(p.x for p in polygon) / len(polygon)
        cy = sum(p.y for p in polygon) / len(polygon)
        cz = sum(p.z for p in polygon) / len(polygon)
        center = _V(cx, cy, cz)

        for i in range(len(polygon) - 2):
            a_vec = polygon[i].minus(center).normalize()
            split_n = plane.normal.cross(polygon[i].minus(center)).normalize()
            split_d = split_n.dot(polygon[i])

            best_angle = -1.0
            best_j = -1
            for j in range(i + 1, len(polygon)):
                if split_n.dot(polygon[j]) - split_d > -EPSILON:
                    b_vec = polygon[j].minus(center).normalize()
                    angle = a_vec.dot(b_vec)
                    if angle > best_angle:
                        best_angle = angle
                        best_j = j

            if best_j == -1:
                return
            polygon[best_j], polygon[i + 1] = polygon[i + 1], polygon[best_j]
