from typing import Optional
try:
    from periphery import SPI
except Exception:
    SPI = None
import time


class MAX6675:
    def __init__(self, spi_device: str, mode: int = 0, max_hz: int = 4000000, samples_avg: int = 1):
        if SPI is None:
            raise RuntimeError("python-periphery SPI not available; install python-periphery or run on target.")
        self.spi = SPI(spi_device, mode, max_hz)
        self.samples_avg = max(1, int(samples_avg))
        self._last_fault = None
        
    def read_c(self) -> Optional[float]:
        temps = []
        for _ in range(self.samples_avg):
            rx = self.spi.transfer([0x00, 0x00])
            val = (rx[0] << 8) | rx[1]
            if val & 0x4:
                self._last_fault = "open"
                return None
            temp_c = ((val >> 3) * 0.25)
            temps.append(temp_c)
            time.sleep(0.01)
        return sum(temps) / len(temps)
    
    def close(self):
        try:
            self.spi.close()
        except Exception:
            pass
