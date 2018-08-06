from flask import Flask, render_template, flash, request
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import dill
import base64
import io
from math import sin,cos, radians
from datetime import datetime, timedelta
import ephem


app = Flask(__name__)

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '7d441f27d441f27567d441111116a'


class ReusableForm(Form):
    where_lat = StringField('Latitude:', validators=[validators.required()])
    where_lon = StringField('Lonitude:', validators=[validators.required()])
    where_lon.data = "120.40"
    where_lat.data = "15:20"


def SolarDeclination(days_in_year):
    " 81st day - Spring Equinox should yield 0"
    SolarDeclination = 23.45 * sin(radians((360 / 365) * (284 + 81)))
    return SolarDeclination


def calc(row):
    """
    Calculate the alledged efficency from Sun Angle to Panel Angle"
    calc: A Pandas Row
    """

    if abs(row['solar_angle'] - row['sun_angle']) > 90:
        return 0
    else:
        if row['solar_angle'] == row['sun_angle']:
            return 1
        else:
            return cos(radians(abs(row['solar_angle'] - row['sun_angle'])))


def calc_2(solar_angle, sun_angle):
    if solar_angle > 0 and solar_angle < 180:

        for sa in range(0, 180, 5):
            if abs(solar_angle - sun_angle) > 90:
                return 0.0
            else:
                if solar_angle == sun_angle:
                    return 1.0
                else:
                    dif = abs(solar_angle - sun_angle)
                    return (cos(radians(abs(solar_angle - sun_angle))))
    else:
        return 0

def big_calc_module(lat="15:20",long="120:40"):
    """
    Calculate Solar heights for 1 year
    Summerize the data - returning a dataframe, and year efficency rating
    :param solar_angle:
    :return:
    """

    from datetime import datetime, timedelta
    from pytz import timezone
    import pandas as pd
    import ephem
    from math import degrees, cos, radians


    fmt = "%Y-%m-%d %H:%M:%S %Z%z"
    fmt_HR = "%H:%M:%S"

    # Telepayong

    obs = ephem.Observer()
    obs.lat=lat
    obs.long=long
    #obs.lat = '15:20'
    #obs.long = '120:40'
    sun_data = {}
    print("Jan 1st 2019")
    # Make timezone aware
    date = datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone('Asia/Manila'))
    # For a year, per week
    for day in range(1, 366 * 24, 1):
        newday = date + timedelta(hours=day)
        newday = newday.astimezone(timezone('Asia/Manila'))
        obsday = newday.astimezone(timezone('UTC'))
        obs.date = obsday
        sun = ephem.Sun(obs)
        sun.compute(obs)
        # Convert to Local times
        utc_rise = datetime.strptime(str(sun.rise_time) + " UTC", "%Y/%m/%d %H:%M:%S %Z").astimezone(timezone('UTC'))
        pi_rise = utc_rise.astimezone(timezone('Asia/Manila'))
        utc_set = datetime.strptime(str(sun.set_time) + " UTC", "%Y/%m/%d %H:%M:%S %Z").astimezone(timezone('UTC'))
        pi_set = utc_rise.astimezone(timezone('Asia/Manila'))

        sun_data[newday.strftime(fmt)] = {"rise": degrees(sun.rise_az),
                                          "set": degrees(sun.set_az),
                                          "rise_time": pi_rise.strftime(fmt_HR),
                                          "set_time": pi_set.strftime(fmt_HR),
                                          "sun_angle": degrees(sun.az)
                                          }
    df_sun_data = pd.DataFrame.from_dict(sun_data, orient='index')





    # Create the New Columns for Calcs
    cols = []
    filter = ""
    for a in range(0, 90, 10):
        a_str = "Angle_{}".format(a)
        e_str = "Eff_{}".format(a)
        df_sun_data[a_str] = a
        df_sun_data[e_str] = 0
        df_sun_data[e_str] = df_sun_data.apply(lambda row: calc_2(row[a_str], row['sun_angle']), axis=1)
        print("Calculated Angle {}".format(a))
        cols.append(e_str)

    df_sun_data['loc'] = 0
    df_sun_data.index = pd.DatetimeIndex(df_sun_data.index)
    # week_res=df_sun_data.groupby('loc').resample('W')[','.join(cols)].mean()

    week_res = df_sun_data.groupby('loc').resample('W')[cols].mean()
    idx = week_res.index.droplevel(level=0)
    week_res.index = pd.DatetimeIndex(idx)
    return week_res,10


def old_calc():
    date = datetime(2016, 7, 18, 0, 0, 0)
    sec_per_year = 3600 * 24 * 365
    tz_offset = 4 * 60 * 60

    obs = ephem.Observer()
    # Telepayong

    flash('Created Observer')
    obs.lat = '23:39'
    obs.long = '58:32'
    old_mon = -1
    data = []
    data.append(("when", "angle", "azimuth"))
    flash('Generating Data')
    for s in range(0, 3600 * 24 * 365, 600):
        stime = date + timedelta(seconds=s)
        obs.date = stime

        sun = ephem.Sun(obs)
        sun.compute(obs)

        localtime = stime + timedelta(seconds=tz_offset)
        sun_angle = float(sun.alt) * 57.2957795  # Convert Radians to degrees
        sun_bearing = float(sun.az) * 57.2957795  # Convert Radians to degrees
        if sun_angle < 0:
            sun_angle = 0
        if sun_angle > 10.0:
            junk = 1
        if s % 7200 == 0:
            print(str.format('{},{:04.1f},{:04.1f}', localtime.strftime("%Y-%m-%d %H:%M:%S"),
                             sun_angle, sun_bearing), end='\n')
        data.append((localtime.strftime("%Y-%m-%d %H:%M:%S"), sun_angle, sun_bearing))

    flash('Writing Data')

    #
    # Data Analysis Section
    #

    dill.dump(data, open("year.data", "wb"))


def plot_to_b64png(df_plot):
    '''

    :param df_plot: the output of df.plot()
    :return: base64 version of img
    '''
    fig = df_plot.get_figure()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    buffer = b''.join(buf)
    b2 = base64.b64encode(buffer)
    b64_plot = b2.decode('utf-8')
    return b64_plot


@app.route("/", methods=['GET', 'POST'])
def where():
    form = ReusableForm(request.form)
    res = {}
    data = {}

    if request.method == 'POST':
        where_lat = request.form['where_lat']
        where_lon = request.form['where_lon']
        #solar_angle = int(request.form['solar_angle'])

        if form.validate():

            res=big_calc_module(lat=where_lat,
                                long=where_lon)

            data[0]={'yeardf':plot_to_b64png(res[0].plot()),
                     'yearavg':res[1]}
        else:
            flash('All the form fields are required. ')

    return render_template('where.html',
                           form=form,
                           where_lat=res,
                           data=data)


if __name__ == '__main__':
    app.run()
