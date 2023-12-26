# tests/test_ndlpy_dataframe.py

import pytest
import ndlpy.data as ndl
import pandas as pd
import numpy as np

from deepdiff import DeepDiff

# Utility function to create test DataFrames
def create_test_dataframe(colspecs="cache"):
    return ndl.CustomDataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]}, colspecs=colspecs)

def create_merged_dataframe():

    # Sample data for creating a CustomDataFrame instance
    data = {"A": [1, 2], "B": [3, 4], "C": [5, 5], "D": [6, 6], "E": [7, 7], "F": [8, 8]}
    colspecs = {"input": ["A", "B"], "output": ["C", "D"], "parameters": ["E", "F"]}
    
    return ndl.CustomDataFrame(data, colspecs=colspecs)
    

# Basic Functionality
def test_dataframe_creation():
    df = create_test_dataframe()
    assert isinstance(df, ndl.CustomDataFrame)
    assert df.shape == (3, 2)

def test_column_access():
    df = create_test_dataframe()
    assert all(df['A'] =={'A': [1, 2, 3]})

def test_row_access():
    df = create_test_dataframe()
    assert all(df.loc[0] == [1, 4])

# Mathematical Operations
def test_sum():
    df = create_test_dataframe()
    assert df.sum().equals(ndl.CustomDataFrame({'A': 6.0, 'B': 15.0}))

def test_mean():
    df = create_test_dataframe()
    assert df.mean().equals(ndl.CustomDataFrame({'A': 2.0, 'B': 5.0}))

# Merging and Joining
def test_concat():
    df1 = create_test_dataframe()
    df2 = create_test_dataframe()
    result = ndl.concat([df1, df2])
    assert result.shape == (6, 2)

def test_merge():
    df1 = ndl.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2']}, colspecs="input")
    df2 = ndl.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2'], 'B': ["B0", "B1", "B2"]}, colspecs="output")
    
    result = df1.merge(df2, on='key')
    print(result)
    assert result.equals(ndl.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A_x': ['A0', 'A1', 'A2'], 'A_y': ['A0', 'A1', 'A2'], 'B': ['B0', 'B1', 'B2']}))
    diff = DeepDiff(result.colspecs, {"input" : ["key", "A_x"], "output" : ["A_y", "B"]})
    assert not diff, "The column specifications don't match in merge"

# Grouping and Sorting
def test_groupby_sum():
    df = ndl.CustomDataFrame({'A': ['foo', 'bar', 'foo', 'bar'], 'B': [1, 2, 3, 4]})
    grouped = df.groupby('A').sum()
    assert grouped.equals(ndl.CustomDataFrame({'B': [4, 6]}, index=['bar', 'foo']))

def test_sort_values():
    df = create_test_dataframe()
    sorted_df = df.sort_values(by='B', ascending=False)
    assert sorted_df.equals(ndl.CustomDataFrame(pd.DataFrame({'A': [3, 2, 1], 'B': [6, 5, 4]}, index=sorted_df.index)))

# I/O Operations (Example: CSV)
def test_to_csv(tmpdir):
    df = create_test_dataframe()
    file_path = tmpdir.join('test.csv')
    df.to_csv(file_path)
    loaded_df = ndl.CustomDataFrame.from_csv(file_path, index_col=0)
    assert df.equals(loaded_df)

# Handling Missing Data
def test_fillna():
    df = ndl.CustomDataFrame({'A': [1, np.nan, 2], 'B': [np.nan, 2, 3]})
    filled_df = df.fillna(0)
    assert filled_df.equals(ndl.CustomDataFrame(pd.DataFrame({'A': [1.0, 0.0, 2.0], 'B': [0.0, 2.0, 3.0]}, index=df.index)))

# Advanced Features (Example: Pivot Table)
def test_pivot_table():
    df = ndl.CustomDataFrame({'A': ['foo', 'foo', 'foo', 'bar', 'bar', 'bar'],
                         'B': ['one', 'one', 'two', 'two', 'one', 'one'],
                         'C': np.random.randn(6),
                         'D': np.random.randn(6)})
    table = df.pivot_table(values='D', index=['A', 'B'], columns=['C'])
    assert isinstance(table, ndl.CustomDataFrame)

# Edge Cases and Error Handling
def test_invalid_data_creation():
    with pytest.raises(ValueError):
        df = ndl.CustomDataFrame({'A': [1, 2], 'B': [3, 4, 5]})



# Test loc accessor
def test_loc_accessor():
    # Test accessing and setting multiple elements
    custom_df = create_merged_dataframe()
    custom_df.loc[0, ["C", "D"]] = [10, 20]
    assert all(custom_df.loc[0, ["C", "D"]] == [[10, 20]])

    # Test accessing 'parameters' type data
    assert custom_df.loc[0, "E"] == 7

    # Test error when modifying 'parameters' with different values
    with pytest.raises(ValueError):
        custom_df.loc[:, "E"] = [[2, 3]]

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
    with pytest.raises(KeyError):
        _ = custom_df.iloc[2, 0]

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
    assert df.iloc[1].equals(ndl.CustomDataFrame(pd.DataFrame({'A': 2, 'B': 5}, index=df.index[1:2])))

def test_boolean_indexing():
    df = create_test_dataframe()
    result = df[df['A'] > 1]
    assert result.equals(ndl.CustomDataFrame(pd.DataFrame({'A': [2, 3], 'B': [5, 6]}, index=result.index)))

# Handling Time Series Data
def test_time_series_indexing():
    time_index = pd.date_range('2020-01-01', periods=3)
    df = ndl.CustomDataFrame(pd.DataFrame({'A': [1, 2, 3]}, index=time_index))
    result = df.loc['2020-01']
    assert len(result) == 3  # Assuming daily data for January 2020

# Data Cleaning
def test_drop_duplicates():
    df = ndl.CustomDataFrame({'A': [1, 1, 2], 'B': [3, 3, 4]})
    result = df.drop_duplicates()
    assert result.equals(ndl.CustomDataFrame(pd.DataFrame({'A': [1, 2], 'B': [3, 4]}, index=result.index)))

# Performance Testing
@pytest.mark.slow
def test_large_dataframe_performance():
    large_df = ndl.CustomDataFrame({'A': range(1000000)})
    result = large_df.sum()
    # Include some form of performance assertion or benchmarking here

# Compatibility with Pandas
def test_compatibility_with_pandas():
    pandas_df = pd.DataFrame({'A': [1, 2, 3]})
    ndl_df = ndl.CustomDataFrame({'A': [1, 2, 3]})
    assert pandas_df.equals(ndl_df.to_pandas())  # Assuming to_pandas() converts ndlpy DataFrame to Pandas DataFrame

# Testing for Exceptions
def test_out_of_bounds_access():
    df = create_test_dataframe()
    with pytest.raises(IndexError):
        _ = df.iloc[10]


# Test __len__ with different sizes of data
def test_len_empty_df():
    data = {}  # Assuming empty DataFrame
    custom_df = ndl.CustomDataFrame(data)
    assert len(custom_df) == 0

def test_len_non_empty_df():
    data = {"col1": [1, 2, 3], "col2": [4, 5, 6]}
    custom_df = ndl.CustomDataFrame(data)
    assert len(custom_df) == 3

def test_len_single_row_df():
    data = {"col1": [1], "col2": [2]}
    custom_df = ndl.CustomDataFrame(data)
    assert len(custom_df) == 1

def test_len_with_series_data():
    data = {"col1": pd.Series([1, 2, 3]), "col2": pd.Series([4, 5, 6])}
    custom_df = ndl.CustomDataFrame(data)
    assert len(custom_df) == 3

def test_len_with_mixed_data_types():
    data = {
        "col1": [1, 2, 3],
        "col2": pd.Series([4, 5, 6]),
        "col3": pd.DataFrame({"subcol1": [7, 8, 9]})
    }
    custom_df = ndl.CustomDataFrame(data)
    assert len(custom_df) == 3

# Add more tests as needed to cover other scenarios and edge cases

