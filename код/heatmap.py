import numpy as np

from PIL import Image

from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter


class HeatMapBuilder:

    @staticmethod
    def build_heatmap(width, height, points, sigma=3):

        if len(points) < 3:
            return None, None, None, None

        xs = np.array([p["x"] for p in points], dtype=np.float32)
        ys = np.array([p["y"] for p in points], dtype=np.float32)
        temps = np.array([p["temp"] for p in points], dtype=np.float32)

        tmin = float(np.min(temps))
        tmax = float(np.max(temps))
        tavg = float(np.mean(temps))

        grid_y, grid_x = np.mgrid[0:height, 0:width]
        grid = griddata((xs, ys), temps, (grid_x, grid_y), method="cubic", fill_value=np.nan)
        mask = np.isnan(grid)

        if np.all(mask):
            return None, tmin, tmax, tavg

        mean_temp = np.nanmean(grid)
        grid[mask] = mean_temp
        grid = gaussian_filter(grid, sigma=sigma)

        if abs(tmax - tmin) < 0.001:
            norm = np.zeros_like(grid)

        else:
            norm = (grid - tmin) / (tmax - tmin)

        norm = np.clip(norm, 0, 1)

        heatmap = np.zeros((height, width, 4), dtype=np.uint8)

        cold = np.array([0, 0, 139], dtype=np.float32)
        hot = np.array([139, 0, 0], dtype=np.float32)
        rgb = (cold * (1 - norm[:, :, None]) + hot * norm[:, :, None])

        heatmap[:, :, :3] = rgb.astype(np.uint8)
        heatmap[:, :, 3] = 180
        heatmap_img = Image.fromarray(heatmap, mode="RGBA" )

        return (heatmap_img, tmin, tmax, tavg)


    @staticmethod
    def overlay(image, heatmap):

        base = image.convert("RGBA")

        return Image.alpha_composite(base, heatmap)


    @staticmethod
    def build_overlay(image, points):

        width, height = image.size
        (heatmap, tmin, tmax, tavg) = HeatMapBuilder.build_heatmap(width, height, points)

        if heatmap is None:
            return (image, tmin, tmax, tavg)

        result = HeatMapBuilder.overlay(image, heatmap)

        return (result, tmin, tmax, tavg)