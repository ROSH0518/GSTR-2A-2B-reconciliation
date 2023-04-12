from flask import Flask, render_template, send_file, make_response,request,session, url_for
import pandas as pd
import os

app = Flask(__name__ ,static_folder='static')
app.secret_key = 'my_secret_key'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/reconcile', methods=['POST'])
def reconcile():
    file1 = request.files['file1']
    file2 = request.files['file2']
    output_file_name = request.form['output_file_name']
    session['output_file_name'] = output_file_name
    print("11",output_file_name)
    reconcile_and_save(file1, file2, output_file_name)
    # get the current working directory
    cwd = os.getcwd()
    # create a link to the Excel file
    link = f'<a href="/download">Download Excel file</a>'
    # render the HTML template with the link
    return render_template('result.html', link=link, output_file_name= output_file_name)

@app.route('/download')
def download():
    output_file_name = session.get('output_file_name')

    # output_file_name = request.args.get('output_file_name')
    print("123",output_file_name)
    file_path = os.path.join(os.getcwd(), output_file_name)

    # create a Flask response object
    response = make_response(send_file(file_path, as_attachment=True))

    # set the filename of the downloaded file
    response.headers.set('Content-Disposition', 'attachment', filename='output.xlsx')

    # return the response object
    return response

def read_purchase_register(file_path):
    mmlDf2 = pd.read_excel(file_path)
    mmlDf2['invDate'] = pd.to_datetime(mmlDf2['invDate'])
    mmlDf = mmlDf2.groupby(['gst', 'name','invNo','invDate'], as_index=False).agg({'invVal': 'sum'})
    return mmlDf

def read_gov_data(file_path):
    govDf = pd.read_excel(file_path)
    govDf['invDate']= pd.to_datetime(govDf['invDate'])
    return govDf

def reconcile_data(mmlDf, govDf):
    same_data_df = pd.merge(mmlDf, govDf, on=['gst', 'invNo'], how='inner', suffixes=('_PurchasRegister', '_2A/2B'))
    same_data_df['diff'] = (same_data_df['invVal_PurchasRegister'] - same_data_df['invVal_2A/2B'])
    same_data = same_data_df[(same_data_df['diff'] >= -5) & (same_data_df['diff'] <= 5)]
    mismatch_value = same_data_df[(same_data_df['diff'] < -5) | (same_data_df['diff'] > 5)]
    return same_data, mismatch_value

def find_different_data(mmlDf, govDf):
    different_data_mml = pd.merge(mmlDf, govDf, on=['gst', 'invNo'], how='outer', indicator=True)
    different_data_gov = different_data_mml[different_data_mml['_merge'] == 'right_only'].drop('_merge', axis=1)
    different_data_mml = different_data_mml[different_data_mml['_merge'] == 'left_only'].drop('_merge', axis=1)
    different_data_mml = different_data_mml.drop(['name_y', 'invVal_y','invDate_y'], axis=1)
    different_data_mml = different_data_mml.rename(columns={'name_x':'name','invVal_x':'invVal','invDate_x':'invDate'})
    different_data_gov = different_data_gov.drop(['name_x', 'invVal_x','invDate_x'], axis=1)
    different_data_gov = different_data_gov.rename(columns={'name_y':'name','invVal_y':'invVal','invDate_y':'invDate'})
    return different_data_mml, different_data_gov

def reconcile_and_save(file_path_mml, file_path_gov, output_file_path):
    mmlDf = read_purchase_register(file_path_mml)
    govDf = read_gov_data(file_path_gov)
    same_data, mismatch_value = reconcile_data(mmlDf, govDf)
    different_data_mml, different_data_gov = find_different_data(mmlDf, govDf)
    writer = pd.ExcelWriter(output_file_path)
    same_data.to_excel(writer, sheet_name='SameData', index=False)
    mismatch_value.to_excel(writer, sheet_name='MismatchValue', index=False)          
    different_data_mml.to_excel(writer, sheet_name='MMLData(notFoundinGov)', index=False)
    different_data_gov.to_excel(writer, sheet_name='GOVData(notFoundinMML)', index=False)
    writer.save()

# if __name__ == '__main__':
#     app.run(debug=True)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')