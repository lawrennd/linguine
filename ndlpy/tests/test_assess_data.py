# tests/test_ndlpy_dataframe.py

import pytest
import ndlpy.assess.data
import ndlpy.config.interface
import pandas as pd
import numpy as np

from deepdiff import DeepDiff


# Utility function to create test DataFrames
def create_test_dataframe(colspecs="cache"):
    return ndlpy.assess.data.CustomDataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]}, colspecs=colspecs)

def create_test_dataframe2(colspecs={"parameters" : ["A"], "writeseries" : ["B"]}):
    return ndlpy.assess.data.CustomDataFrame({'A': [1, 1, 1], 'B': [4, 5, 6]}, colspecs=colspecs)

def create_merged_dataframe():
    # Sample data for creating a CustomDataFrame instance
    data = {"A": [1, 2], "B": [3, 4], "C": [5, 5], "D": [6, 6], "E": [7, 7], "F": [8, 8]}
    colspecs = {"input": ["A", "B"], "output": ["C", "D"], "parameters": ["E", "F"]}
    
    return ndlpy.assess.data.CustomDataFrame(data, colspecs=colspecs)

def create_series_dataframe():
    # Sample data for creating a CustomDataFrame instance
    data = {"A": [1, 2], "B": [3, 4], "C": [5, 5], "D": [6, 6], "E": [7, 7], "F": [8, 8]}
    colspecs = {"input": ["A", "B"], "output": ["C", "D"], "writeseries": ["E", "F"]}
    
    return ndlpy.assess.data.CustomDataFrame(data, colspecs=colspecs)


# test creation of a dataframe
def test_dataframe_creation():
    df = create_test_dataframe()
    assert isinstance(df, ndlpy.assess.data.CustomDataFrame)
    assert df.shape == (3, 2)

# test creation of an empty dataframe
def test_empty_dataframe_creation():
    df = ndlpy.assess.data.CustomDataFrame({})
    assert isinstance(df, ndlpy.assess.data.CustomDataFrame)
    assert df.empty

# Test column access to data frame
def test_column_access():
    df = create_test_dataframe()
    assert all(df['A'] == pd.Series(data=[1, 2, 3], index=df.index, name="A"))

def test_row_access():
    df = create_test_dataframe()
    assert all(df.loc[0] == [1, 4])

# Mathematical Operations
def test_sum():
    df = create_test_dataframe()
    assert df.sum().equals(ndlpy.assess.data.CustomDataFrame({'A': 6, 'B': 15}))

def test_mean():
    df = create_test_dataframe()
    assert df.mean().equals(ndlpy.assess.data.CustomDataFrame({'A': 2.0, 'B': 5.0}))

# Merging and Joining
def test_concat():
    df1 = create_test_dataframe()
    df2 = create_test_dataframe()
    result = ndlpy.assess.data.concat([df1, df2])
    assert result.shape == (6, 2)

def test_merge():
    df1 = ndlpy.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2']}, colspecs="input")
    df2 = ndlpy.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2'], 'B': ["B0", "B1", "B2"]}, colspecs="output")
    
    result = df1.merge(df2, on='key')
    assert result.equals(ndlpy.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A_x': ['A0', 'A1', 'A2'], 'A_y': ['A0', 'A1', 'A2'], 'B': ['B0', 'B1', 'B2']}))
    diff = DeepDiff(result.colspecs, {"input" : ["key", "A_x"], "output" : ["A_y", "B"]})
    assert not diff, "The column specifications don't match in merge"

# test join
def test_join():
    df1 = ndlpy.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2']}, colspecs="input")
    df2 = ndlpy.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2'], 'B': ["B0", "B1", "B2"]}, colspecs="output")
    
    result = df1.join(df2, lsuffix="_1", rsuffix="_2")
    assert result.equals(ndlpy.assess.data.CustomDataFrame({'key_1': ['K0', 'K1', 'K2'], 'A_1': ['A0', 'A1', 'A2'], 'key_2': ['K0', 'K1', 'K2'], 'A_2': ['A0', 'A1', 'A2'], 'B': ['B0', 'B1', 'B2']}))
    diff = DeepDiff(result.colspecs, {"input" : ["key_1", "A_1"], "output" : ["key_2", "A_2", "B"]})
    assert not diff, "The column specifications don't match in join"


def test_to_flow_valid_output(mocker):
    mocker.patch('ndlpy.access.io.write_data')
    test_df = ndlpy.assess.data.CustomDataFrame({})
    test_df._d = {'output': 'some_data'}
    
    interface = {'output': {'param1': 'value1'}}
    
    test_df.to_flow(interface)
    ndlpy.access.io.write_data.assert_called_with('some_data', {'param1': 'value1'})

def test_to_flow_invalid_interface():
    test_df = ndlpy.assess.data.CustomDataFrame({})
    test_df.types = {'output': ['output_type']}
    
    with pytest.raises(ValueError):
        test_df.to_flow(None)  # None is not a valid interface

def test_to_flow_no_output_data(mocker):
    mocker.patch('ndlpy.assess.data.log.warning')
    test_df = ndlpy.assess.data.CustomDataFrame({})
    test_df._d = {'non_output_type': 'some_data'}
    
    interface = {'output_type': [{'param1': 'value1'}]}
    
    test_df.to_flow(interface)
    ndlpy.assess.data.log.warning.assert_called()

def test_to_flow_no_data_is_none(mocker):
    mocker.patch('ndlpy.assess.data.log.warning')
    test_df = ndlpy.assess.data.CustomDataFrame({})
    test_df._d = {'non_output_type': None}
    
    interface = {'output_type': [{'param1': 'value1'}]}
    
    test_df.to_flow(interface)
    ndlpy.assess.data.log.warning.assert_called()
    
def test_to_flow_error_in_write_data(mocker):
    mocker.patch('ndlpy.access.io.write_data', side_effect=Exception("Test error"))
    mocker.patch('ndlpy.assess.data.log.error')
    test_df = ndlpy.assess.data.CustomDataFrame({})
    test_df._d = {'output': 'some_data'}
    
    interface = {'output': [{'param1': 'value1'}]}
    
    test_df.to_flow(interface)
    ndlpy.assess.data.log.error.assert_called()
    
@pytest.fixture
def valid_local_settings():
    # Return a sample interface object that is valid
    return ndlpy.config.interface.Interface({
        "input":
        {
            "type" : "local",
            "index" : "index",
            "data" : [
            {
                'index': 'indexValue',
                'key1': 'value1',
                'key2': 'value2',
                'key3': 'value3',
            }],
            "select" : 'indexValue'
        }
    })
@pytest.fixture
def valid_local_select_settings():
    # Return a sample interface object that is valid
    return ndlpy.config.interface.Interface({
        "parameters":
        {
            "type" : "local",
            "index" : "index",
            "select" : "indexValue2",
            "data" : [
            {
                'index': 'indexValue',
                'key1': 'value1',
                'key2': 'value2',
                'key3': 'value3',
            },
            {
                'index': 'indexValue2',
                'key1': 'value1row2',
                'key2': 'value2row2',
                'key3': 'value3row2',
            }],
        }
    })

# test from_flow with a valid setting that specifies local data.
def test_from_flow_with_valid_settings(valid_local_settings):
    cdf = ndlpy.assess.data.CustomDataFrame.from_flow(valid_local_settings)
    assert isinstance(cdf, ndlpy.assess.data.CustomDataFrame)
    assert cdf == ndlpy.assess.data.CustomDataFrame(pd.DataFrame({'key1': 'value1', 'key2' : 'value2', 'key3': 'value3'}, index=['indexValue']))
    assert cdf.colspecs == {"input" : ["key1", "key2", "key3"]}

# test from_flow with a valid setting that specifies local data.
def test_from_flow_with_valid_select_settings(valid_local_select_settings):
    cdf = ndlpy.assess.data.CustomDataFrame.from_flow(valid_local_select_settings)
    assert isinstance(cdf, ndlpy.assess.data.CustomDataFrame)
    assert cdf == ndlpy.assess.data.CustomDataFrame(pd.DataFrame({'key1': 'value1row2', 'key2' : 'value2row2', 'key3': 'value3row2'}, index=[0]))
    assert cdf.colspecs == {"parameters" : ["key1", "key2", "key3"]}
    
def test_from_flow_with_invalid_type():
    with pytest.raises(ValueError):
        ndlpy.assess.data.CustomDataFrame.from_flow("not-a-dictionary")

def test_from_flow_with_missing_keys():
    incomplete_settings = ndlpy.config.interface.Interface({
        # Settings with missing keys
        "key1": "value1",
    })
    with pytest.raises(ValueError):
        ndlpy.assess.data.CustomDataFrame.from_flow(incomplete_settings)

def test_from_flow_with_empty_settings():
    cdf = ndlpy.assess.data.CustomDataFrame.from_flow(ndlpy.config.interface.Interface({"globals":
                                                           {"type" : "local",
                                                            "data" : {},
                                                            "index" : "index"}}))
    # Assert the result is as expected (empty dataframe, etc.)
    assert isinstance(cdf, ndlpy.assess.data.CustomDataFrame)
    assert cdf.empty


    
# Grouping and Sorting
def test_groupby_sum():
    df = ndlpy.assess.data.CustomDataFrame({'A': ['foo', 'bar', 'foo', 'bar'], 'B': [1, 2, 3, 4]})
    grouped = df.groupby('A').sum()
    assert grouped.equals(pd.DataFrame({'B': [6, 4]}, index=pd.Index(['bar', 'foo'], name="A")))

def test_sort_values():
    df = create_test_dataframe()
    sorted_df = df.sort_values(by='B', ascending=False)
    assert sorted_df.equals(ndlpy.assess.data.CustomDataFrame(pd.DataFrame({'A': [3, 2, 1], 'B': [6, 5, 4]}, index=sorted_df.index)))

# I/O Operations (Example: CSV)
def test_to_csv(tmpdir):
    df = create_test_dataframe()
    file_path = tmpdir.join('test.csv')
    df.to_csv(file_path)
    loaded_df = ndlpy.assess.data.CustomDataFrame.from_csv(file_path, index_col=0)
    assert df.equals(loaded_df)

# Handling Missing Data
def test_fillna():
    df = ndlpy.assess.data.CustomDataFrame({'A': [1, np.nan, 2], 'B': [np.nan, 2, 3]})
    filled_df = df.fillna(0)
    assert filled_df.equals(ndlpy.assess.data.CustomDataFrame(pd.DataFrame({'A': [1.0, 0.0, 2.0], 'B': [0.0, 2.0, 3.0]}, index=df.index)))

# Advanced Features (Example: Pivot Table)
def test_pivot_table():
    df = ndlpy.assess.data.CustomDataFrame({'A': ['foo', 'foo', 'foo', 'bar', 'bar', 'bar'],
                         'B': ['one', 'one', 'two', 'two', 'one', 'one'],
                         'C': np.random.randn(6),
                         'D': np.random.randn(6)})
    table = df.pivot_table(values='D', index=['A', 'B'], columns=['C'])
    assert isinstance(table, ndlpy.assess.data.CustomDataFrame)

def create_sample_dataframes():
    return {
        'df1': pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']}),
        'df2': pd.DataFrame({'B': [4.0, 5.0, 6.0], 'C': [True, False, True]})
    }

def test_dtypes_with_consistent_columns():
    data = create_sample_dataframes()
    custom_df = ndlpy.assess.data.CustomDataFrame(data["df1"])
    expected_dtypes = pd.Series({'A': np.dtype('int64'), 'B': np.dtype('object')})
    diff = DeepDiff(custom_df.dtypes, expected_dtypes)
    assert not diff, "The df dtypes don't match expectations"

    custom_df = ndlpy.assess.data.CustomDataFrame(data["df2"])
    expected_dtypes = pd.Series({'B': np.dtype('float64'), 'C': np.dtype('bool')})
    diff = DeepDiff(custom_df.dtypes, expected_dtypes)
    assert not diff, "The df dtypes don't match expectations"


def test_dtypes_with_empty_dataframe():
    data = {'df1': pd.DataFrame()}
    custom_df = ndlpy.assess.data.CustomDataFrame(data)
    assert custom_df.dtypes.empty

def test_dtypes_with_no_subframes():
    custom_df = ndlpy.assess.data.CustomDataFrame({})
    assert custom_df.dtypes.empty
    
# Edge Cases and Error Handling
def test_invalid_data_creation():
    with pytest.raises(ValueError):
        df = ndlpy.assess.data.CustomDataFrame({'A': [1, 2], 'B': [3, 4, 5]})


# Test ismutable method
def test_ismutable():
    custom_df = create_test_dataframe(colspecs="input")
    assert custom_df.ismutable("A") == False
    custom_df = create_test_dataframe(colspecs="output")
    assert custom_df.ismutable('B') == True
    custom_df = create_test_dataframe2()
    assert custom_df.ismutable('A') == True

# Test mutable property
def test_mutable():
    custom_df = create_test_dataframe(colspecs="input")
    custom_df.autocache=False
    assert custom_df.mutable == False
    custom_df = create_test_dataframe(colspecs="output")
    assert custom_df.mutable == True

# Test isseries method
def test_isseries():
    custom_df = create_test_dataframe(colspecs="output")
    assert custom_df.isseries("A") == False
    custom_df = create_test_dataframe(colspecs="series")
    assert custom_df.isseries('B') == True
    custom_df = create_test_dataframe2()
    assert custom_df.isseries('A') == False
    
    
# Test _col_source method
def test_col_source():
    custom_df = create_test_dataframe(colspecs={"input": ["A"], "output": ["B"]})
    assert custom_df._col_source('A') == 'input'
    assert custom_df._col_source('B') == 'output'
    custom_df = create_test_dataframe(colspecs={"writeseries": ["A"], "cache": ["B"]})
    assert custom_df._col_source('A') == 'writeseries'
    assert custom_df._col_source('B') == 'cache'  # Assuming autocache is True

# Test isparameter method
def test_isparameter():
    custom_df = create_test_dataframe2(colspecs={"globals": ["A"], "writeseries": ["B"]})
    assert custom_df.isparameter('A') == True
    assert custom_df.isparameter('B') == False

# Test isseries method
def test_isseries():
    custom_df = create_test_dataframe2(colspecs={"globals": ["A"], "writeseries": ["B"]})
    assert custom_df.isseries('A') == False
    assert custom_df.isseries('B') == True


        
# Test get_selectors()
def test_get_selectors():
    custom_df = create_merged_dataframe()
    assert custom_df.get_selectors() == []

    custom_df = create_series_dataframe()
    assert custom_df.get_selectors() == ["E", "F"]
    
# Test loc accessor
def test_loc_accessor():
    # Test accessing and setting multiple elements
    custom_df = create_merged_dataframe()
    custom_df.loc[0, ["C", "D"]] = [10, 20]
    assert all(custom_df.loc[0, ["C", "D"]] == [10, 20])

    # Test accessing 'parameters' type data
    assert custom_df.loc[0, "E"] == 7

    # Test error when modifying 'parameters' with different values
    with pytest.raises(ValueError):
        custom_df.loc[:, "E"] = [2, 3]

    # Test setting value in 'output' type
    custom_df.loc[1, "C"] = 30
    assert custom_df.loc[1, "C"] == 30

    # Test error when modifying 'input' type
    with pytest.raises(KeyError):
        custom_df.loc[0, "A"] = 50

# Test iloc accessor
def test_iloc_accessor():
    # Test accessing multiple elements by integer location
    custom_df = create_merged_dataframe()
    assert all(custom_df.iloc[0, [2, 3]] == [10, 20])

    # Test error on invalid index
    with pytest.raises(IndexError):
        _ = custom_df.iloc[2, 0]

    # Test accessing 'parameters' type data
    assert custom_df.iloc[1, 4] == 7

    # Test error when modifying 'parameters' with different values
    with pytest.raises(ValueError):
        custom_df.iloc[:, 4] = [2, 3]

    # Test setting value in 'output' type
    custom_df.iloc[1, 2] = 30
    assert custom_df.loc[1, "C"] == 30

    # Test error when modifying 'input' type
    with pytest.raises(KeyError):
        custom_df.iloc[0, 0] = 50
        

# Test at accessor
def test_at_accessor():
    # Test accessing single element
    custom_df = create_merged_dataframe()
    assert custom_df.at[0, "A"] == 1

    # Test setting single element in 'output' type
    custom_df.at[1, "C"] = 40
    assert custom_df.at[1, "C"] == 40

    # Test error when modifying 'input' type
    with pytest.raises(KeyError):
        custom_df.at[0, "B"] = 60


def test_iloc():
    df = create_test_dataframe()
    assert df.iloc[1].equals(ndlpy.assess.data.CustomDataFrame(pd.DataFrame({'A': 2, 'B': 5}, index=df.index[1:2])))

def test_boolean_indexing():
    df = create_test_dataframe()
    result = df[df['A'] > 1]
    assert result.equals(ndlpy.assess.data.CustomDataFrame(pd.DataFrame({'A': [2, 3], 'B': [5, 6]}, index=result.index)))

# Handling Time Series Data
def test_time_series_indexing():
    time_index = pd.date_range('2020-01-01', periods=3)
    df = ndlpy.assess.data.CustomDataFrame(pd.DataFrame({'A': [1, 2, 3]}, index=time_index))
    result = df.loc['2020-01']
    assert len(result) == 3  # Assuming daily data for January 2020

# Data Cleaning
def test_drop_duplicates():
    df = ndlpy.assess.data.CustomDataFrame({'A': [1, 1, 2], 'B': [3, 3, 4]})
    result = df.drop_duplicates()
    assert result.equals(ndlpy.assess.data.CustomDataFrame(pd.DataFrame({'A': [1, 2], 'B': [3, 4]}, index=result.index)))

# Performance Testing
@pytest.mark.slow
def test_large_dataframe_performance():
    large_df = ndlpy.assess.data.CustomDataFrame({'A': range(1000000)})
    result = large_df.sum()
    # Include some form of performance assertion or benchmarking here

# Compatibility with Pandas
def test_compatibility_with_pandas():
    pandas_df = pd.DataFrame({'A': [1, 2, 3]})
    ndl_df = ndlpy.assess.data.CustomDataFrame({'A': [1, 2, 3]})
    assert pandas_df.equals(ndl_df.to_pandas())  # Assuming to_pandas() converts ndlpy DataFrame to Pandas DataFrame

# Testing for Exceptions
def test_out_of_bounds_access():
    df = create_test_dataframe()
    with pytest.raises(IndexError):
        _ = df.iloc[10]


# Test __len__ with different sizes of data
def test_len_empty_df():
    data = {}  # Assuming empty DataFrame
    custom_df = ndlpy.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 0

def test_len_non_empty_df():
    data = {"col1": [1, 2, 3], "col2": [4, 5, 6]}
    custom_df = ndlpy.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 3

def test_len_single_row_df():
    data = {"col1": [1], "col2": [2]}
    custom_df = ndlpy.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 1

def test_len_with_series_data():
    data = {"col1": pd.Series([1, 2, 3]), "col2": pd.Series([4, 5, 6])}
    custom_df = ndlpy.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 3

def test_len_with_mixed_data_types():
    data = {
        "col1": [1, 2, 3],
        "col2": pd.Series([4, 5, 6]),
        "col3": ["two", "four", "six"],
    }
    custom_df = ndlpy.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 3


@pytest.fixture
def custom_dataframe():
    # Setup for CustomDataFrame instance
    df = ndlpy.assess.data.CustomDataFrame([{"col1": "value1", "col2": "value2"}])
    df._name_column_map = {}  # Assuming _name_column_map is a dict
    df._column_name_map = {}  # Assuming _column_name_map is a dict
    return df

def test_update_name_column_map(custom_dataframe):
    # Test updating with a new name-column pair
    custom_dataframe.update_name_column_map("var_name", "column_name")
    assert custom_dataframe._name_column_map["var_name"] == "column_name"
    assert custom_dataframe._column_name_map["column_name"] == "var_name"

    # Test updating with an existing column but a new name
    with pytest.raises(ValueError):
        custom_dataframe.update_name_column_map("new_var_name", "column_name")

def test_default_mapping(custom_dataframe):
    custom_dataframe._name_column_map = {"var1": "col1", "var2": "col2"}
    assert custom_dataframe._default_mapping() == {"var1": "col1", "var2": "col2"}

def test_mapping_with_default(custom_dataframe):
    # Assuming set_column and get_value methods are part of CustomDataFrame
    custom_dataframe._name_column_map = {"var1": "col1", "var2": "col2"}
    mapping_result = custom_dataframe.mapping()
    assert mapping_result == {"var1": "value1", "var2": "value2"}

def test_mapping_with_provided_series(custom_dataframe):
    custom_dataframe._name_column_map = {"var1": "col1", "var2": "col2"}
    provided_series = pd.Series({"col1": "value1", "col2": "value2"})
    mapping_result = custom_dataframe.mapping(series=provided_series)
    assert mapping_result == {"var1": "value1", "var2": "value2"}

def test_mapping_nan_removal(custom_dataframe):
    custom_dataframe._name_column_map = {"var1": "col1", "var2": "col2"}
    custom_dataframe.set_column("col2")
    custom_dataframe.set_value(None)
    mapping_result = custom_dataframe.mapping()
    assert mapping_result == {"var1": "value1"} 

