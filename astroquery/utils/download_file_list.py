import StringIO
import re
import string
import os
import gzip
import astropy.io.fits as fits
import astropy.utils.data as aud

__all__ = ['download_list_of_fitsfiles']

whitespace_re = re.compile("\s")
valid_chars = "-_.()%s%s" % (string.ascii_letters, string.digits)

def validify_filename(filestr):
    """ Remove invalid characters from a file string """
    filestr = filestr.strip()
    filestr = whitespace_re.sub("_",filestr)

    # strip out invalid characters
    filestr = "".join([c for c in filestr if c in valid_chars])
    return filestr

def download_list_of_fitsfiles(linklist, output_directory=None,
        output_prefix=None, save=False, overwrite=False, verbose=False,
        output_coord_format=None, filename_header_keywords=None,
        include_input_filename=True):
    """
    Given a list of file URLs, download them and (optionally) rename them

    example:
    download_list_of_fitsfiles(
        ['http://fermi.gsfc.nasa.gov/FTP/fermi/data/lat/queries/L130413170713F15B52BC06_PH00.fits',
         'http://fermi.gsfc.nasa.gov/FTP/fermi/data/lat/queries/L130413170713F15B52BC06_PH01.fits',
         'http://fermi.gsfc.nasa.gov/FTP/fermi/data/lat/queries/L130413170713F15B52BC06_SC00.fits'],
         output_directory='fermi_m31',
         output_prefix='FermiLAT',
         save=True,
         overwrite=False,
         verbose=True,
         output_coord_format=None, # FITS tables don't have crval/crpix, good one is: "%08.3g%+08.3g",
         filename_header_keywords=None, # couldn't find any useful ones
         include_input_filename=True)

    """
    # Loop through links and retrieve FITS images
    images = {}
    for link in linklist:

        if output_directory is None:
            output_directory = ""
        elif output_directory[-1] != "/":
            output_directory += "/"
            if not os.path.exists(output_directory):
                os.mkdir(output_directory)

        with aud.get_readable_fileobj(link, cache=True) as f:
            results = f.read()
        S = StringIO.StringIO(results)

        try: 
            # try to open as a fits file
            fitsfile = fits.open(S,ignore_missing_end=True)
        except IOError:
            # if that fails, try to open as a gzip'd fits file
            # have to rewind to the start
            S.seek(0)
            G = gzip.GzipFile(fileobj=S)
            fitsfile = fits.open(G,ignore_missing_end=True)

        # Get Multiframe ID from the header
        images[link] = fitsfile

        if save:
            h0 = fitsfile[0].header

            if filename_header_keywords: # is not None or empty
                nametxt = "_".join([validify_filename(str(h0[key])) for key in filename_header_keywords])
            else:
                nametxt = ""

            if output_coord_format:
                lon = h0['CRVAL1']
                lat = h0['CRVAL2']

                # this part will eventually be handled by astropy.coordinates directly
                # ctype = h0['CTYPE1']
                # if 'RA' in ctype:
                #     coordinate = coord.ICRSCoordinates(lon,lat,unit=('deg','deg'))
                # elif 'GLON' in ctype:
                #     coordinate = coord.GalacticCoordinates(lon,lat,unit=('deg','deg'))
                # else:
                #     raise TypeError("Don't recognize ctype %s" % ctype)
                # coordstr = coordinate.format(output_coord_format)
                try:
                    coordstr = output_coord_format.format(lon,lat)
                except TypeError:
                    coordstr = output_coord_format % (lon,lat)
                nametxt += "_" + coordstr

            if include_input_filename:
                filename_root = os.path.split(link)[1]
            else:
                filename_root = ""
        
            savename = output_prefix if output_prefix else ""
            savename += nametxt
            savename += "_" + filename_root

            # Set final directory and file names
            final_file = output_directory + savename

            if verbose:
                print "Saving file %s" % final_file

            try:
                fitsfile.writeto(final_file, clobber=overwrite)
            except IOError:
                print "Skipped writing file %s because it exists and overwrite=False" % final_file

    return images
