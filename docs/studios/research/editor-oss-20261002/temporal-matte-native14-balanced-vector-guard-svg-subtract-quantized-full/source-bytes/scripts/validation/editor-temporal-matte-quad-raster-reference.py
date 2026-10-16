"""Independent large affine quad coverage for the pinned four-bit rasterizer.

Construct a half-pixel convex annulus mathematically, project its vertices to
the source/runtime-declared subpixel grid, and interpolate coverage in triangles.
No renderer code, browser pixels or DOM geometry supplies the reference.
"""
import math


def polygon_orientation(polygon):
    return 1 if sum(x * polygon[(i + 1) % len(polygon)][1] - y * polygon[(i + 1) % len(polygon)][0]
                    for i, (x, y) in enumerate(polygon)) > 0 else -1


def offset_polygon(polygon, distance):
    sign = polygon_orientation(polygon)
    lines = []
    for i, (x, y) in enumerate(polygon):
        dx, dy = polygon[(i + 1) % len(polygon)][0] - x, polygon[(i + 1) % len(polygon)][1] - y
        length = math.hypot(dx, dy)
        nx, ny = -sign * dy / length, sign * dx / length
        lines.append((nx, ny, nx * x + ny * y + distance))
    result = []
    for i, (a, b, c) in enumerate(lines):
        d, e, f = lines[i - 1]
        det = a * e - b * d
        assert abs(det) > 1e-10, "degenerate_quad_reference_pending"
        result.append(((c * e - b * f) / det, (a * f - c * d) / det))
    return result


def triangle_coverage(vertices, values, x, y):
    (ax, ay), (bx, by), (cx, cy) = vertices
    det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(det) < 1e-12:
        return None
    first = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / det
    second = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / det
    third = 1 - first - second
    if min(first, second, third) < -1e-10:
        return None
    return max(0, min(1, first * values[0] + second * values[1] + third * values[2]))


def quad_triangles(polygon, subpixel_bits=4):
    assert len(polygon) == 4 and subpixel_bits == 4
    scale = 1 << subpixel_bits
    inner = [(round(x * scale) / scale, round(y * scale) / scale) for x, y in offset_polygon(polygon, .5)]
    outer = [(round(x * scale) / scale, round(y * scale) / scale) for x, y in offset_polygon(polygon, -.5)]
    triangles = [([inner[0], inner[1], inner[2]], [1, 1, 1]), ([inner[0], inner[2], inner[3]], [1, 1, 1])]
    for i in range(4):
        following = (i + 1) % 4
        triangles.extend([([inner[i], inner[following], outer[following]], [1, 1, 0]),
                          ([inner[i], outer[following], outer[i]], [1, 0, 0])])
    return triangles


def texture_triangles(polygon, inverse_matrix):
    """Compile independently constructed projected triangles and authored UVs."""
    inner, outer = offset_polygon(polygon, .5), offset_polygon(polygon, -.5)
    indexes = [(('i', 0), ('i', 1), ('i', 2)), (('i', 0), ('i', 2), ('i', 3))]
    for i in range(4):
        following = (i + 1) % 4
        indexes.extend([(('i', i), ('i', following), ('o', following)),
                        (('i', i), ('o', following), ('o', i))])
    a, b, c, d, e, f = inverse_matrix
    result = []
    for triangle in indexes:
        original = [(inner if kind == 'i' else outer)[index] for kind, index in triangle]
        projected = [(round(px * 16) / 16, round(py * 16) / 16) for px, py in original]
        local = [(a * px + c * py + e, b * px + d * py + f) for px, py in original]
        result.append((projected, local))
    return result


def interpolate_texture_coordinates(triangles, x, y):
    for projected, local in triangles:
        first = triangle_coverage(projected, [1, 0, 0], x, y)
        if first is None:
            continue
        second = triangle_coverage(projected, [0, 1, 0], x, y)
        third = 1 - first - second
        weights = [first, second, third]
        return (sum(weight * u for weight, (u, v) in zip(weights, local, strict=True)),
                sum(weight * v for weight, (u, v) in zip(weights, local, strict=True)))
    return None


def interpolate_affine_coordinates(polygon, inverse_matrix, x, y):
    """Interpolate authored local coordinates on the projected large quad."""
    return interpolate_texture_coordinates(texture_triangles(polygon, inverse_matrix), x, y)


def coverage(triangles, x, y):
    for triangle, values in triangles:
        result = triangle_coverage(triangle, values, x, y)
        if result is not None:
            return result
    return 0


def byte(value):
    return max(0, min(255, math.floor(value + .5)))


def serial_channel(quad, clip=None, image=None):
    result = byte(quad * byte(.85 * 255))
    if clip is not None:
        alpha = byte(clip * 255)
        if image is not None:
            alpha = byte(alpha * byte(image * 255) / 255)
        result = byte(result * alpha / 255)
    for opacity in [.9, .9]:
        result = byte(result * byte(opacity * 255) / 255)
    return result
