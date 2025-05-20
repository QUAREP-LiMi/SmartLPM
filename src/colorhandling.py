"""    
This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

class ColorHandler:
    # This class is an adaptation to Python of the algorithm by Dan Bruton
    # http://www.physics.sfasu.edu/astro/color/spectra.html, http://www.midnightkite.com/color.html 
    def waveLengthToRGB(Wavelength):

        Gamma = 0.80
        IntensityMax = 255


        if(Wavelength < 380):
            Red = 1.0
            Green = 0.0
            Blue = 1.0
        elif((Wavelength >= 380) and (Wavelength < 440)):
            Red = -(Wavelength - 440) / (440 - 380)
            Green = 0.0
            Blue = 1.0
        elif((Wavelength >= 440) and (Wavelength < 490)):
            Red = 0.0
            Green = (Wavelength - 440) / (490 - 440)
            Blue = 1.0
        elif((Wavelength >= 490) and (Wavelength < 510)):
            Red = 0.0
            Green = 1.0
            Blue = -(Wavelength - 510) / (510 - 490)
        elif((Wavelength >= 510) and (Wavelength < 580)):
            Red = (Wavelength - 510) / (580 - 510)
            Green = 1.0
            Blue = 0.0
        elif((Wavelength >= 580) and (Wavelength < 645)):
            Red = 1.0
            Green = -(Wavelength - 645) / (645 - 580)
            Blue = 0.0
        elif(Wavelength >= 645):
            Red = 1.0
            Green = 0.0
            Blue = 0.0

        rgb = [Red,Green,Blue]

        # Attenuate intensities towards IR and UV:

        if((Wavelength >= 380) and (Wavelength < 420)):
            attenuation = 0.3 + 0.7 * (Wavelength - 380) / (420 - 380)
        elif((Wavelength >= 420) and (Wavelength < 701)):
            attenuation = 1.0
        elif((Wavelength >= 701) and (Wavelength < 781)):
            attenuation = 0.3 + 0.7 * (780 - Wavelength) / (780 - 700)
        else:
            attenuation = 0.2 # IR ^ UV
        
        rgb[0] = 0 if Red == 0.0 else round(IntensityMax * (Red * attenuation) ** Gamma)
        rgb[1] = 0 if Green == 0.0 else round(IntensityMax * (Green * attenuation) ** Gamma)
        rgb[2] = 0 if Blue == 0.0 else round(IntensityMax * (Blue * attenuation) ** Gamma)

        return rgb
        