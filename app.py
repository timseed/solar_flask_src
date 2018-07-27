from flask import Flask, render_template, flash, request
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import ephem
import pickle
import dill
from datetime import datetime, timedelta
import pandas as pd
from matplotlib import pyplot
import base64
import io
from math import degrees

app = Flask(__name__)

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '7d441f27d441f27567d441111116a'


class ReusableForm(Form):
    where_lat = StringField('Latitude:', validators=[validators.required()])
    where_lon = StringField('Lonitude:', validators=[validators.required()])
    where_lon.data = "120.40"
    where_lat.data = "15:20"


def calc():
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
    sunmaxalt2 = None
    sunriseset2 = None

    if request.method == 'POST':
        where_lat = request.form['where_lat']
        where_lon = request.form['where_lon']

        if form.validate():
            ## Save the comment here.
            flash('Lat ' + str(where_lat) + "Lon " + str(where_lon))
            date = datetime(2016, 7, 18, 0, 0, 0)
            sec_per_year = 3600 * 24 * 365
            tz_offset = 4 * 60 * 60

            obs = ephem.Observer()

            flash('Created Observer')
            # Telepayong
            obs.lat = '15:20'
            obs.long = '120:40'
            old_mon = -1
            sun_angle_data = []
            sun_rise_set_data = []
            sun_angle_data.append(("when", "angle", "azimuth"))
            #sun_rise_set_data.append(("when", "rise_bearing", "set_bearing"))
            #flash('Generating Data')
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
                # if s % 7200 == 0:
                #    print(str.format('{},{:04.1f},{:04.1f}', localtime.strftime("%Y-%m-%d %H:%M:%S"),
                #                     sun_angle, sun_bearing), end='\n')
                sun_angle_data.append((localtime.strftime("%Y-%m-%d %H:%M:%S"), sun_angle, sun_bearing))

            flash('Writing Data')
            #dill.dump(sun_angle_data, open("year.data", "wb"))
            #sun_angle_data = pickle.load(open("year.data", "rb"))

            df = pd.DataFrame(sun_angle_data[1:], columns=sun_angle_data[0])



            # Telepayong
            obs = ephem.Observer()
            obs.lat = '15:20'
            obs.long = '120:40'
            sun_rise_set_data = {}

            # Make time gmt +9 i.e. PDT
            date = datetime(2016, 7, 18, 9, 0, 0)
            # For a year, per week
            for day in range(1, 366, 7):
                newday = date + timedelta(days=day)
                obs.date = newday
                sun = ephem.Sun(obs)
                sun.compute(obs)
                sun_rise_set_data[newday.strftime("%Y-%m-%d %H:%M:%S")] = {"rise": degrees(sun.rise_az),
                                                                           "set": degrees(sun.set_az)}
            df_sun_rise_set_week = pd.DataFrame.from_dict(sun_rise_set_data, orient='index')
            df_sun_rise_set_week['Mean_Rise'] = df_sun_rise_set_week.rise.mean()
            df_sun_rise_set_week['Mean_Set'] = df_sun_rise_set_week.set.mean()
            #Make Index DateTime aware
            df_sun_rise_set_week.index = pd.DatetimeIndex(df_sun_rise_set_week.index)

            def make_date_time(x):
                try:
                    rv = datetime.strptime(str(x), '%Y-%m-%d %H:%M:%S')
                except:
                    rv = datetime(1990, 1, 1, 1, 1)
                return rv

            flash("Create DateTime Column")
            df['DT'] = df.when.apply(make_date_time)
            flash("Drop unused column")
            df.drop(['when'], axis=1, inplace=True)
            # print("Set Index to DateTime Column")
            df.set_index(df.DT, drop=True, inplace=True)
            flash("Initial Calcs done")
            # Remote the times when the sum has not risen more than 5 Degrees
            df = df[df.angle > 5]
            flash("Removed angle < 5")
            angle_ser = pd.Series(df.angle, index=df.DT)
            az_ser = pd.Series(df.azimuth, index=df.DT)
            flash("Creating some Series")
            week_max_angle = angle_ser.resample('W').max()

            week_max_az = az_ser.resample('W').max()
            flash('Create Data Frames')
            df_week_max_angle = pd.DataFrame.from_dict(week_max_angle.to_dict(),
                                                       orient='index', columns=['max_angle'])

            flash('DF Finished')
            sunmaxalt2 = plot_to_b64png(df_week_max_angle.plot())
            sunriseset2 = plot_to_b64png(df_sun_rise_set_week.plot())

        else:
            flash('All the form fields are required. ')

    return render_template('where.html', form=form,
                           where_lat=res,
                           sunmaxalt=sunmaxalt2,
                           sunriseset=sunriseset2)


if __name__ == '__main__':
    app.run()
