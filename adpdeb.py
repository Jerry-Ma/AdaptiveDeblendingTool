#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2014-09-26 01:08
# Python Version :  2.7.5
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
"""
adpdeb.py

Open up the `IDE` for deblending

ds9
    frames: lowres, highres, model, residue
    region: highres position, grouped with redshift, sex obj in residue
    tool:   catalogue selection window
"""

import pyds9
from astropy.io import fits
import types
import numpy as np
import os
import subprocess
import time
import uuid

import utils


class SourceSelector(object):

    def __init__(self, **kwargs):

        self.hi_res_map_list = kwargs['hi_res_map_list']
        self.hi_res_cat_list = kwargs['hi_res_cat_list']
        self.hi_res_label = kwargs['hi_res_label']
        self.hi_res_coord_index = kwargs['hi_res_coord_index']

        self.low_res_map_list = kwargs['low_res_map_list']
        self.low_res_noise_list = kwargs['low_res_noise_list']
        self.low_res_cat = np.loadtxt(
            kwargs['low_res_cat'],
            dtype=zip(*utils.get_ascii_table_header(kwargs['low_res_cat'])),
            ndmin=1)
        self.low_res_label = kwargs['low_res_label']
        self.low_res_beamsize = kwargs['low_res_beamsize']
        self.low_res_coord_index = kwargs['low_res_coord_index']
        self.low_res_ps = kwargs['low_res_ps']
        self.low_res_psf = os.path.abspath(kwargs['low_res_psf'])

        self.galfit_workroot = os.path.abspath(kwargs['galfit_workroot'])
        self.galfit_bin = os.path.abspath(kwargs['galfit_bin'])
        self.xclip_bin = os.path.abspath(kwargs['xclip_bin'])
        self.xpa_extracmd = kwargs['xpa_extracmd']

        self.lastwarning = ""
        self._result_loaded = False

        self.ds9 = pyds9.DS9("DS9-GalFit"
                             )
        self.clean_display()

    def load_object_by_ind(self, ind):

        self.ind = ind
        self.hi_res_map = os.path.abspath(self.hi_res_map_list[ind])
        self.hi_res_cat = os.path.abspath(self.hi_res_cat_list[ind])
        self.low_res_map = os.path.abspath(self.low_res_map_list[ind])
        self.low_res_noise = os.path.abspath(self.low_res_noise_list[ind])
        self.low_res_info = self.low_res_cat[ind]
        self.low_res_coord = (self.low_res_info[self.low_res_coord_index[0]],
                              self.low_res_info[self.low_res_coord_index[1]])
        self.low_res_xsize, self.low_res_ysize = self.get_low_res_size()
        self.galfit_work = 'gfwork_{0:d}'.format(ind + 1)
        self.galfit_fits = 'galfit_out_{0:d}'.format(ind + 1)
        self.galfit_logfile = 'gflog_{0:d}.html'.format(ind + 1)

        self.low_res_wcs = self.get_low_res_wcs()
        with open('wcs.dump', 'w') as fo:
            fo.write(self.low_res_wcs)
        self.clean_display()

    def show_label(self, text):
        ra, dec = map(float, self.ds9.get('pan wcs fk5').strip().split())
        offset = utils.radius_str_to_degree(self.low_res_beamsize)
        self.ds9set(
            ('regions',
            'fk5;text %f %f # color=red text={%s}'
            % (ra, dec + 1.2 * offset, text))
                   )

    def ds9set(self, *args):
        ''' to wrap for error prove'''
        for i in args:
            try:
                if isinstance(i, (tuple, list)):
                    self.ds9.set(*i)
                elif isinstance(i, types.FunctionType):
                    i()
                else:
                    self.ds9.set(i)
            except ValueError as e:
                e = str(e).strip()
                if self.lastwarning != e:
                    print "[!] {0:s}".format(e)
                self.lastwarning = e

    def get_low_res_size(self):
        hdulist = fits.open(self.low_res_map)
        return int(hdulist[0].header['NAXIS1']), int(hdulist[0].header['NAXIS2'])

    def get_low_res_wcs(self):
        hdulist = fits.open(self.low_res_map)
        try:
            wcs = '''CRPIX1 =   {CRPIX1:f}
CRPIX2 =   {CRPIX2:f}
CRVAL1 =   {CRVAL1:f}
CRVAL2 =   {CRVAL2:f}
CDELT1 =   {CDELT1:f}
CDELT2 =   {CDELT2:f}
CTYPE1 =   '{CTYPE1:s}'
CTYPE2 =   '{CTYPE2:s}'
'''.format(**hdulist[0].header)
        except KeyError:
            return ''
        try:
            wcs_cd = '''
CD1_1 =    {CD1_1:f}
CD2_1 =    {CD2_1:f}
CD1_2 =    {CD1_2:f}
CD2_2 =    {CD2_2:f}
'''.format(**hdulist[0].header)
            return '\n'.join([wcs, wcs_cd])
        except KeyError:
            return wcs

    def clean_display(self):
        while True:
            try:
                self.ds9.set('catalog close')
            except ValueError:
                break
        self.ds9set('frame delete 3')
        self.ds9set('frame delete 4')
        self.ds9set('frame clear all')
        self.ds9set('lock scale no')
        self.ds9set('lock scale no')
        self.ds9set('contour no')

    def load_display(self, ex_command=None):
        command = [
            'contour smooth 1',
            'contour nlevels 5',
            'contour color blue',
            'contour dash yes',
            'lock colorbar yes',
            'tile',
            'zscale',
            'cmap invert',
            'frame 1',
            'file {%s}' % (self.hi_res_map),
            'frame 2',
            'file {%s}' % (self.low_res_map),
            'frame lock wcs',
            'pan to %s %s wcs fk5' % self.low_res_coord,
            ]
        command = command + self.xpa_extracmd
        if not ex_command is None:
            command = command + ex_command
        self.ds9set(*command)
        self._scale = self.ds9.get('scale limits')
        self.show_label('')
        self._result_loaded = False

    def load_result(self):
        if self._result_loaded:
            self.ds9.set('catalog close')
        command = [
            'frame 2',
            'regions select all',
            'regions copy',
            'regions select none',
            'contour yes',
            'frame 3',
            'file {%s[2]}' % (os.path.join(self.galfit_workroot,
                                           self.galfit_work,
                                           self.galfit_fits)),
            ('wcs append', self.low_res_wcs),
            'regions paste',
            'scale limits %s' % (self._scale),
            'contour yes',
            lambda: self.show_label('Model'),
            'frame 4',
            'file {%s[3]}' % (os.path.join(self.galfit_workroot,
                                           self.galfit_work,
                                           self.galfit_fits)),
            ('wcs append', self.low_res_wcs),
            'regions paste',
            'scale limits %s' % (self._scale),
            'contour yes',
            lambda: self.show_label('Residue'),
            'frame 2',
                ]
        self.ds9set(*command)
        self.show_hi_res_catalog(frame=4)
        self._result_loaded = True

    def show_low_res_coord(self, frame=0):
        ofid = int(self.ds9.get('frame frameno'))
        if isinstance(frame, (long, int)):
            if frame > 0:
                fid = [frame, ]
            else:
                fid = map(int, self.ds9.get('frame all').split())
        for i in fid:
            self.ds9set(
                'frame {0:d}'.format(i),
                'region delete all',
                ('regions', 'fk5;circle %s %s %s # color=red tag={target}'
                    % (self.low_res_coord[0], self.low_res_coord[1],
                       self.low_res_beamsize)),
                )
            if i == 2:
                self.show_label(self.low_res_label)
            if i == 1:
                self.show_label(self.hi_res_label)

        self.ds9set('frame {0:d}'.format(ofid))

    def show_hi_res_catalog(self, frame=0):
        ofid = int(self.ds9.get('frame frameno'))
        if isinstance(frame, (long, int)):
            if frame > 0:
                fid = [frame, ]
            else:
                fid = map(int, self.ds9.get('frame all').split())
        for i in fid:
            self.ds9set(
                'frame {0:d}'.format(i),
                'catalog import tsv %s' % (self.hi_res_cat),
                )
            header = [j.split('=')[-1] for j in
                        self.ds9.get('catalog header').split('\n')]
            self.ds9set('catalog x %s' % (header[self.hi_res_coord_index[0]]),
                        'catalog y %s' % (header[self.hi_res_coord_index[1]]),
                        )
        self.ds9set('frame {0:d}'.format(ofid),
                    'mode catalog')

    def _get_selected_hi_res_xy(self):
        for i, j in enumerate(self.selected):
            self.ds9set(
            ('regions',
            'fk5;point %s %s # color=cyan point=circle tag={sel} text={No.%d}'
            % (j[self.hi_res_coord_index[0]], j[self.hi_res_coord_index[1]],
               i+1))
            )
        xy = [i.split() for i in self.ds9.get(
            'regions -format xy -system image -group {sel}').split('\n')]
        return xy

    def pretty_print_selected(self):

        info = []
        header, _ = utils.get_ascii_table_header(self.hi_res_cat)
        info.append('+-- %-15s %-15s' % (header[self.hi_res_coord_index[0]],
                                         header[self.hi_res_coord_index[1]]))
        for i in self.selected:
            info.append('    %-15s %-15s' % (i[self.hi_res_coord_index[0]],
                                             i[self.hi_res_coord_index[1]]))
        return '\n'.join(info)

    def gen_galfit_parfile(self):
        par_global = '''
# IMAGE and GALFIT CONTROL PARAMETERS
A) {low_res_map:s}            # Input data image (FITS file)
B) {galfit_fits:s}       # Output data image block
C) {low_res_noise:s}        # Sigma image name (made from data if blank or "none")
D) {low_res_psf:s}   #        # Input PSF image and (optional) diffusion kernel
E) 1                   # PSF fine sampling factor relative to data
F) none                # Bad pixel mask (FITS image or ASCII coord list)
G) none                # File with parameter constraints (ASCII file)
H) 1 {low_res_xsize:d} 1 {low_res_ysize:d}  # Image region to fit (xmin xmax ymin ymax)
I) {low_res_xsize:d} {low_res_ysize:d}      # Size of the convolution box (x y)
J) 26.4              # Magnitude photometric zeropoint
K) {low_res_ps:f} {low_res_ps:f}   # Plate scale (dx dy)    [arcsec per pixel]
O) regular             # Display type (regular, curses, both)
P) 0                   # Choose: 0=optimize, 1=model, 2=imgblock, 3=subcomps

# INITIAL FITTING PARAMETERS
#
#   For object type, the allowed functions are:
#       nuker, sersic, expdisk, devauc, king, psf, gaussian, moffat,
#       ferrer, powsersic, sky, and isophote.
#
#   Hidden parameters will only appear when they're specified:
#       C0 (diskyness/boxyness),
#       Fn (n=integer, Azimuthal Fourier Modes),
#       R0-R10 (PA rotation, for creating spiral structures).
#
# -----------------------------------------------------------------------------
#   par)    par value(s)    fit toggle(s)    # parameter description
# -----------------------------------------------------------------------------
'''.format(**self.__dict__)
        par_obj = []
        for i, j in enumerate(self._get_selected_hi_res_xy()):
            par_obj.append('''
# Object number: {objnum:d}
 0) psf                 #  object type
 1) {posx:s} {posy:s} 0 0  #  position x, y
 3) {mag_init:d}     1          #  Integrated magnitude
 Z) 0                      #  output option (0 = resid., 1 = Don't subtract)
'''.format(objnum=i, mag_init=i + 24, posx=j[0], posy=j[1]))

        for path in [self.galfit_workroot,
                     os.path.join(self.galfit_workroot, self.galfit_work)]:
            if not os.path.isdir(path):
                os.makedirs(path)
                print ' + {0:s}'.format(path)
        with open(os.path.join(self.galfit_workroot,
                               self.galfit_work,
                               'autogen_galfit.par'),
                  'w') as fo:
            fo.write(par_global)
            for i in par_obj:
                fo.write(i)
        return par_global + ''.join(par_obj)

    def _parse_result(self, gf_cont):
        logfile = os.path.join(self.galfit_workroot,
                               self.galfit_work,
                               'fit.log')
        with open(logfile, 'r') as fo:
            content = fo.read().split('{0:s}\n{0:s}'.format('-'*77))
        return '{0:s}'.format('-'*77) + '\n' + content[-1]

    def run_galfit(self):
        # when run galfit, we need to switch to the work dir
        oldpwd = os.getcwd()
        os.chdir(os.path.join(self.galfit_workroot, self.galfit_work))
        gf_cont = subprocess.check_output(
            [self.galfit_bin, 'autogen_galfit.par'])
        os.chdir(oldpwd)
        if r"Fit summary is now being saved into `fit.log'." in gf_cont:
            self.galfit_result = self._parse_result(gf_cont)
        else:
            self.galfit_result = ""
        return gf_cont

    def write_to_log(self):
        logfile = os.path.join(self.galfit_workroot,
                               self.galfit_work,
                               self.galfit_logfile)
        # validate the logfile:
        neednewone = False
        try:
            with open(logfile, 'r') as fo:
                content = fo.read()
            if not 'DS9-GalFit Adaptive De-blending Tool Logfile' in content\
                    or not content.strip().startswith("<html><body>")\
                    or not content.strip().endswith("</body></html>"):
                # not a real one
                os.rename(logfile,
                          logfile + '_{0:s}.bak'.format(
                              time.strftime("%Y-%m-%d_%H:%M:%S")))
                neednewone = True
        except IOError:
            neednewone = True
        if neednewone:
            with open(logfile, 'w') as fo:
                fo.write(
                    '''<html><body>
                    <h1>DS9-GalFit Adaptive De-blending Tool Logfile<h1>
                    <table>
                    </table></body></html>''')
        # compose parameter string
        logfile_entry = """
        <tr>
        <td><pre>{0:s}</pre></td>
        <td><img src="{1:s}"></td>
        </tr>
        </table></body></html>"""
        galfit_log = """Time: {0:s}
+-- Deblending of obj. {1:d}
 [low-res map  ] {4:s}
 [low-res noise] {5:s}
 [low-res psf  ] {6:s}
 [low_res coord] {7:f} {8:f}
 -------------------------
 [hi-res map   ] {2:s}
 [hi_res cat   ] {3:s}
 [hi_res_select]
 {9:s}
 -------------------------
 {10:s}
""".format(time.strftime("%Y-%m-%d %H:%M:%S"),
           self.ind + 1,
           self.hi_res_map,
           self.hi_res_cat,
           self.low_res_map,
           self.low_res_noise,
           self.low_res_psf,
           self.low_res_coord[0], self.low_res_coord[1],
           self.pretty_print_selected(),
           self.galfit_result if self.galfit_result != "" else "GalFit fails!")
        # save image
        thumbnail = self.save_thumbnail()
        logfile_entry = logfile_entry.format(galfit_log, os.path.basename(thumbnail))
        with open(logfile, 'r') as fo:
            content = fo.read()
        content = content.replace("</table></body></html>", logfile_entry)
        with open(logfile, 'w') as fo:
            fo.write(content)

    def save_thumbnail(self):
        thumb_name = os.path.join(self.galfit_workroot,
                                  self.galfit_work,
                                  "thumb_{0:s}.png".format(uuid.uuid4()))
        self.ds9set("saveimage {0:s}".format(thumb_name))
        return thumb_name
