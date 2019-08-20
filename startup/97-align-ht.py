from bluesky.callbacks.mpl_plotting import plot_peak_stats
from bluesky.callbacks.fitting import PeakStats


HT_X_START = 8.70
HT_Y_START = -85.96
HT_COORDS_FILE = str(PROFILE_STARTUP_PATH / 'ht_coords.csv')
HT_COORDS_FILE_OLD = str(PROFILE_STARTUP_PATH / 'ht_coords_old.csv')
LOAD_POS_X = -50
LOAD_POS_Y = -50

#TODO: add qem2 once it's repared
QUADEM_DETS = [qem1]
ALIGN_DETS = {x.name: x for x in QUADEM_DETS + [tcm1]}


class TestMode:
    def __init__(self, test_mode=False):
        self._test_mode = test_mode
        self._valid_values = (True, False)

    @property
    def test_mode(self):
        return self._test_mode

    @test_mode.setter
    def test_mode(self, test_mode):
        assert any([test_mode is x for x in self._valid_values]), \
            f'The value should be one of {self._valid_values}'
        self._test_mode = test_mode

mode = TestMode(test_mode=False)


def align_ht(x_start=HT_X_START, y_start=HT_Y_START, md=None, offset=3.5, run=True,
             det=tcm1):
    """Align high-throughput sample holder.

        x_start : horizontal start position
        y_start : vertical start position
        md : optional metadata information
    """
    assert det in ALIGN_DETS.values(), \
        f'The detector for alignment should be one of {list(ALIGN_DETS.keys())}'

    global HT_COORDS, HT_COORDS_OLD, _x_start, _y_start
    _x_start = None
    _y_start = None
    if run:
        fig = plt.figure('Align with <{}> motor and <{}> detector'.format(ht.name, det.name),
                         figsize=(16, 5))
        ax_hor = fig.add_subplot(121)
        ax_ver = fig.add_subplot(122)
        def close_shutters():
            yield from bps.mv(shutter, 'Close')
            if not mode.test_mode:
                yield from bps.mv(pps_shutter, 'Close')
            yield from bps.mv(ht.x, LOAD_POS_X, ht.y, LOAD_POS_Y)  # load position

        def main_plan():
            global PS_X, PS_Y, _x_start, _y_start
            yield from bps.mv(ht.x, x_start-offset, ht.y, y_start)
            if not mode.test_mode:
                yield from bps.mv(pps_shutter, 'Open')
            if det.name in QUADEM_DETS:
                yield from bps.mv(getattr(det.current_offset_calcs, f'ch{det.read_attrs[0].replace("current", "")}'), 1)

            # Find uid and peak stats for horizontal calibration:
            uid, PS_X = yield from _align_ht('horizontal', ht.x,
                                             x_start-offset, x_start+offset, 141,
                                             md=md, det=det, ax=ax_hor)

            # Move hor. position to COM before we scan vertical one:
            yield from bps.mv(ht.x, PS_X.com, ht.y, y_start-offset)

            uid, PS_Y = yield from _align_ht('vertical', ht.y,
                                             y_start-offset, y_start+offset, 141,
                                             md=md, det=det, ax=ax_ver)
            # Move both hor. & vert. positions to COM after alignment:
            yield from bps.mv(ht.x, PS_X.com, ht.y, PS_Y.com)

            _x_start = PS_X.com
            _y_start = PS_Y.com

        yield from bpp.finalize_wrapper(main_plan(),
                                        close_shutters())
    else:
        _x_start = x_start
        _y_start = y_start

    if os.path.isfile(HT_COORDS_FILE):
        os.rename(HT_COORDS_FILE, HT_COORDS_FILE_OLD)
        HT_COORDS_OLD = HT_COORDS

    HT_COORDS = default_coords(x_start=_x_start, y_start=_y_start)
    HT_COORDS.to_csv(HT_COORDS_FILE, float_format='%.2f')


def default_coords(x_start=HT_X_START, y_start=HT_Y_START, 
                   x_init_slot=2, y_init_slot=0,
                   n_cols=8, n_rows=12,
                   x_spacing=9.0, y_spacing=9.0):
    """Default coordinates for the HT sample holder.

        x_start : horizontal start position
        y_start : vertical start position
        x_init_slot : horizontal slot number to align
        y_init_slot : vertical slot number to align
        n_cols : number of columns
        n_rows : number of rows
        x_spacing : distance between slots in horizontal direction
        y_spacing : distance between slots in vertical direction

    """
    ht_coords = []
    for i in range(n_rows):
        ht_coords.append([])
        for j in range(n_cols):
            ht_coords[-1].append([
                x_start + (j - x_init_slot) * x_spacing,
                y_start + (i - y_init_slot) * y_spacing,
            ])
    ht_coords = np.array(ht_coords)
    ht_coords = np.reshape(ht_coords, (n_cols*n_rows, 2))
    return pd.DataFrame(ht_coords, columns=['x', 'y'])


def _align_ht(dir_name, mtr,
              start, stop, num_points, *,
              md=None, det=tcm1, ax=None):
    det_name = list(det.read().keys())[0]
    lp = LivePlot(f'{det_name}', mtr.name, ax=ax)
    ps = PeakStats(mtr.name, f'{det_name}')

    _md = {'purpose': 'table alignment',
           'plan_name': '_align_ht',
           'dir_name': dir_name}
    _md.update(md or {})

    # fire the fast shutter and wait for it to close again
    yield from bps.mv(dg, 600)  # generate 600-seconds pulse
    yield from bps.mv(dg.fire, 1)
    yield from bps.mv(shutter, 'Open')  # open the protective shutter

    uid = yield from bpp.subs_wrapper(
            bp.scan([det],
                     mtr,
                     start, stop, num_points,
                     md=_md),
            [lp, ps])
    xfp_print({k: v for k, v in ps.__dict__.items() if not k.startswith('_')})

    ax.set_title(f'COM: {ps.com:.2f} mm  FWHM: {ps.fwhm:.2f} mm')

    yield from bps.mv(shutter, 'Close')  # close the protective shutter
    yield from bps.mv(dg, 0)  # set delay to 0 (causes interruption of the current pulse)

    yield from bps.checkpoint()

    return (uid, ps)

