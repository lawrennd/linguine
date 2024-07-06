import pandas as pd
import numpy as np

from .. import access
from ..log import Logger
from ..config.context import Context
from ..config.interface import Interface
from ..util.misc import remove_nan, to_camel_case, is_valid_var

from ..assess.compute import Compute

"""Wrapper classes for data objects"""

ctxt = Context()
log = Logger(
    name=__name__,
    level=ctxt._data["logging"]["level"],
    filename=ctxt._data["logging"]["filename"],
)


class Accessor:
    def __init__(self, data):
        self._data_object = data

    def __getitem__(self, key):
        raise NotImplementedError("This is a base accessor class")

    def __setitem__(self, key, value):
        raise NotImplementedError("This is a base accessor class")


class DataObject:
    def __init__(
            self, data=None, colspecs=None, index=None, column=None, selector=None, subindex=None
    ):
        self.at = self._AtAccessor(self)
        self.iloc = self._IlocAccessor(self)
        self.loc = self._locAccessor(self)

    class _AtAccessor(Accessor):
        def __init__(self, data):
            super().__init__(data=data)

    class _LocAccessor(Accessor):
        def __init__(self, data):
            super().__init__(data=data)

    class _IlocAccessor(Accessor):
        def __init__(self, data):
            super().__init__(data=data)

    def get_subindex(self):
        raise NotImplementedError("This is a base class")

    def set_subindex(self, val):
        raise NotImplementedError("This is a base class")


    def get_subseries(self) -> pd.DataFrame:
        """
        Get the subseries that is the focus for the DataFrame.

        :return: The subseries that is the focus for the DataFrame.
        """
        # The series types are stored in cls.types["series"]
        # Extract DataFrames from that class and merge them.
        series = None
        for typ in self.types["series"]:
            if typ in self.colspecs:
                data = self[self.colspecs[typ]]
                if series is None:
                    series = data
                else:
                    series = series.join(data, how="outer")

        # Use the in focus index to choose which part of the series is returned.
        return series[series.index.isin([self.get_index()])]
    

    def get_subindices(self) -> pd.Index:
        """
        Get the subindices that are the focus for the DataFrame.

        :return: The subindices that are the focus for the DataFrame.
        """
        
        if self._selector is None:
            return []
        try:
            subseries = self.get_subseries()[self._selector]
            return pd.Index(subseries.values, name=self._selector, dtype="object")
        except KeyError as err:
            raise KeyError(f"Could not find index \"{err}\" in the subseries when using it as a selector.")

    def get_index(self) -> int:
        """
        Get the index that is the focus for the DataFrame.

        :return: The index that is the focus for the DataFrame.
        """
        return self._index

    def set_index(self, index : int) -> None:
        """
        Set the index to be the focus for the DataFrame.

        :param index: The index to set.
        :raise KeyError: If the index is not in the DataFrame.
        """
        if index is None:
            log.debug("Setting index to None.")
            self._index = None
        elif index in self.index:
            log.debug(f"Setting index to {index}.")
            self._index = index
        else:
            raise KeyError("Invalid index set.")

    def get_column(self):
        """
        Get the column that is the focus for the DataFrame.

        :return: The column that is the focus for the DataFrame.
        """
        return self._column

    def set_column(self, column):
        """
        Set the column to be the focus for the DataFrame.

        :param column: The column to set.
        :raise KeyError: If the column is not in the DataFrame.
        """
        if column == "_":
            self._column = "_"
            log.warning(f"Set column to \"_\".")
            return
        if column is None:
            if len(self.columns) == 0:
                self._column = None
                log.warning(f"Set column to \"{self._column}\".")
                return
            errmsg = f"Was asked to set column to None."
            log.warning(errmsg)
            raise KeyError(errmsg)
            # Note column is not being set here.
            return

        if column not in self.columns and column!=self.index.name:
            # In the vrs 0.1.0 this used to warn and run self.add_column(column)
            errmsg = f"Attempting to add column \"{column}\" as a set request has been given to non existent column."
            log.warning(errmsg)
            raise KeyError(errmsg)
        else:
            self._column = column
    def set_value_column(self, value, column):
        """
        Set a value to a column in the write data frame

        :param value: The value to be set.
        :type value: object
        :param column: The column to set the value in.
        :type column: str
        :return: None
        """
        orig_col = self.get_column()
        self.set_column(column)
        self.set_value(value)
        if orig_col is not None:
            self.set_column(orig_col)

    def get_value_column(self, column):
        """
        Get a value from a column in the data frame(s)

        :param column: The column to get the value from.
        :type column: str
        :return: The value from the column.
        :rtype: object
        """
        orig_col = self.get_column()
        self.set_column(column)
        value = self.get_value()
        if orig_col is not None:
            self.set_column(orig_col)
        return value

    def ismutable(self, column):
        """
        Is a given column mutable?

        :param column: The column to check.
        :return: True if the column is mutable, False otherwise.
        """
        if column not in self.columns:
            if self.autocache:
                return True
            else:
                return False

        if self._col_source(column) in self.types["input"]:
            return False
        else:
            return True

    def isseries(self, column):
        """
        Is a given column a series column?

        :param column: The column to check.
        :return: True if the column is a series column, False otherwise.
        """
        if self._col_source(column) in self.types["series"]:
            return True
        else:
            return False
        
    @property
    def autocache(self):
        """
        Whether the data structure will automatically cache values.

        :return True if the data structure will automatically cache values, False otherwise.
        """
        if self._autocache:
            return True
        else:
            return False

    @autocache.setter
    def autocache(self, value):
        """
        Set whether the data structure will automatically cache values.

        :param value: The value to set.
        :raise ValueError: If the value is not boolean.
        """
        
        if not isinstance(value, bool):
            raise ValueError(f"autocache value must be boolean, set as \"{value}\"")
        self._autocache = value

    @property
    def interface(self):
        """
        Return the interface object.
        :return: The interface object.
        """
        return self._interface

    @interface.setter
    def interface(self, value):
        """
        Set the interface object.
        :param value: The interface object.
        :return: None
        """
        if not isinstance(value, Interface):
            raise TypeError("interface must be of type Interface.")
        else:
            self._interface = value
        
    @property
    def mutable(self):
        """
        Is the data structure mutable.

        :return True if the data structure is mutable, False otherwise.
        """
        if self.autocache:
            return True
        for typ in self._d:
            if typ not in self.types["input"]:
                return True
        return False
        
    def _col_source(self, column):
        """
        Return the source of a column.

        :param column: The column to check.
        """
        for typ, data in self._d.items():
            if typ in self.types["parameters"]:
                if column in data.index:
                    return typ
            elif column in data.columns:
                return typ
        if self.autocache:
            return "cache"
        else:
            return None

    def isparameter(self, column):
        """
        Test if the column is a given column a parameter (i.e. applicable for all rows)?

        :param column: The column to check.
        :return: True if the column is a parameter, False otherwise.
        """
        if self._col_source(column) in self.types["parameters"]:
            return True
        else:
            return False
        
    def isseries(self, column):
        """
        Test if a given column is a series column (i.e. one where the index can be repeated and have multiple rows associated with it).

        :param column: The column to check.
        :return: True if the column is a series column, False otherwise.
        """
        if self._col_source(column) in self.types["series"]:
            return True
        else:
            return False
        

        
        
    def get_selector(self):
        """
        Get the selector that is the focus for the DataFrame.

        The selector is the column used to disambiguate a series in
        the focus.

        :return: The selector that is the focus for the DataFrame.
        """
        return self._selector

    def set_selector(self, column):
        """
        Set the selector that is the focus for the DataFrame.

        The selector

        :param column: The column to set the selector to.
        :raise KeyError: If the column is not in the DataFrame.
        """
        if column is None:
            self._selector = None
        elif column in self.columns:
            self._selector = column
        else:
            raise KeyError("Invalid selector set.")

    def get_subindex(self) -> int:
        """
        Get the subindex that is the focus for the DataFrame.
        The subindex is the index used to disambiguate a series in
        the focus.

        :return: The subindex that is the focus for the DataFrame.
        """
        return self._subindex

    def set_subindex(self, index : int):
        """
        Set the subindex that is the focus for the DataFrame.

        :param index: The index to set the subindex to.
        :raise KeyError: If the index is not in the DataFrame.
        """
        if index is None:
            self._subindex = None
        elif index in self.index:
            self._subindex = index
        else:
            raise KeyError("Invalid subindex set.")
        
    def get_selectors(self):
        """
        Return valid selectors, these are columns that are present in the type "series"
        :return: The valid selectors.
        """

        # iterate through the colspecs finding columns of type series
        selectors = [
            col
            for typ in self.types["series"]
            for col in self.colspecs.get(typ, [])
        ]
        
        if self._selector is not None and self._selector in selectors:
            # Return selectors with selector at front (to ensure it is default) for widgets)
            selectors.insert(0, selectors.pop(selectors.index(self._selector)))
        return selectors
        
    def get_value(self):
        """
        Get the value that is in the cell defined as focus for the DataFrame.

        :return: The value that is the focus for the DataFrame.
        """
        # Check whether the column is a series column.

        col = self.get_column()
        if col == self.index.name:
            return self.get_index()
        val = self.at[self.get_index(), col]
        if self.isseries(col):
            # If it is a series column, return the element of val where the self._selector column equals the self._subindex value.
            if self._selector is None:
                raise KeyError("Selector not set.")
            if self._subindex is None:
                raise KeyError("Subindex not set.")
            return val[val[self._selector] == self._subindex]
        return val
            
            

    def set_value(self, value):
        """
        Set the value that is in the cell defined as focus for the DataFrame.

        :param value: The value to set.
        """
        self.at[self.get_index(), self.get_column()] = value

    def head(self, n=5):
        """
        Return the first `n` rows of the DataFrame.

        :param n: Number of rows to select.
        :return: The first `n` rows of the DataFrame.
        """
        return self.to_pandas().head(n)

    def tail(self, n=5):
        """
        Return the last `n` rows of the DataFrame.

        :param n: Number of rows to select.
        :return: The last `n` rows of the DataFrame.
        """
        return self.to_pandas().tail(n)

    def add_column(self, column_name, data):
        """
        Add a new column to the DataFrame.

        :param column_name: The name of the new column.
        :param data: The data for the new column.
        :raise NotImplementedError: Indicates the method needs to be implemented in a subclass.
        """
        raise NotImplementedError("This is a base class")

    def drop_column(self, column_name):
        """
        Drop a column from the DataFrame.

        :param column_name: The name of the column to drop.
        :raise NotImplementedError: Indicates the method needs to be implemented in a subclass.
        """
        raise NotImplementedError("This is a base class")

    def filter_rows(self, condition):
        """
        Filter rows based on a specified condition.

        :param condition: The condition to filter rows.
        :raise NotImplementedError: Indicates the method needs to be implemented in a subclass.
        """
        raise NotImplementedError("This is a base class")

    def get_shape(self):
        """
        Get the shape of the DataFrame.

        :return: A tuple representing the shape of the DataFrame.
        """
        return self.to_pandas().shape

    def describe(self):
        """
        Generate descriptive statistics.

        :return: Descriptive statistics for the DataFrame.
        """
        return self.to_pandas().describe()

    def to_pandas(self):
        """
        Convert the custom DataFrame to a Pandas DataFrame.

        :raise NotImplementedError: Indicates the method needs to be implemented in a subclass.
        """
        raise NotImplementedError("This is a base class")

    def to_clipboard(self, *args, **kwargs):
        """
        Copy the DataFrame to the system clipboard.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_clipboard.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_clipboard.
        :return: Output of Pandas DataFrame to_clipboard method.
        """
        return self.to_pandas().to_clipboard(*args, **kwargs)

    def to_feather(self, *args, **kwargs):
        """
        Write the DataFrame to a Feather file.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_feather.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_feather.
        :return: Output of Pandas DataFrame to_feather method.
        """
        return self.to_pandas().to_feather(*args, **kwargs)

    def to_json(self, *args, **kwargs):
        """
        Convert the DataFrame to a JSON string.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_json.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_json.
        :return: Output of Pandas DataFrame to_json method.
        """
        return self.to_pandas().to_json(*args, **kwargs)

    def to_orc(self, *args, **kwargs):
        """
        Write the DataFrame to an ORC file.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_orc.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_orc.
        :return: Output of Pandas DataFrame to_orc method.
        """
        return self.to_pandas().to_orc(*args, **kwargs)

    def to_records(self, *args, **kwargs):
        """
        Convert the DataFrame to a NumPy record array.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_records.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_records.
        :return: Output of Pandas DataFrame to_records method.
        """
        return self.to_pandas().to_records(*args, **kwargs)

    def to_timestamp(self, *args, **kwargs):
        """
        Cast to DatetimeIndex of timestamps.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_timestamp.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_timestamp.
        :return: Output of Pandas DataFrame to_timestamp method.
        """
        return self.to_pandas().to_timestamp(*args, **kwargs)

    def to_csv(self, *args, **kwargs):
        """
        Write the DataFrame to a comma-separated values (csv) file.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_csv.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_csv.
        :return: Output of Pandas DataFrame to_csv method.
        """
        return self.to_pandas().to_csv(*args, **kwargs)

    def to_gbq(self, *args, **kwargs):
        """
        Write the DataFrame to a Google BigQuery table.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_gbq.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_gbq.
        :return: Output of Pandas DataFrame to_gbq method.
        """
        return self.to_pandas().to_gbq(*args, **kwargs)

    def to_latex(self, *args, **kwargs):
        """
        Render the DataFrame as a LaTeX tabular environment table.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_latex.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_latex.
        :return: Output of Pandas DataFrame to_latex method.
        """
        return self.to_pandas().to_latex(*args, **kwargs)

    def to_parquet(self, *args, **kwargs):
        """
        Write the DataFrame to a Parquet file.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_parquet.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_parquet.
        :return: Output of Pandas DataFrame to_parquet method.
        """
        return self.to_pandas().to_parquet(*args, **kwargs)

    def to_sql(self, *args, **kwargs):
        """
        Write records stored in the DataFrame to a SQL database.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_sql.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_sql.
        :return: Output of Pandas DataFrame to_sql method.
        """
        return self.to_pandas().to_sql(*args, **kwargs)

    def to_xarray(self, *args, **kwargs):
        """
        Convert the DataFrame to an xarray Dataset.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_xarray.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_xarray.
        :return: Output of Pandas DataFrame to_xarray method.
        """
        return self.to_pandas().to_xarray(*args, **kwargs)

    def to_dict(self, *args, **kwargs):
        """
        Convert the DataFrame to a dictionary.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_dict.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_dict.
        :return: Output of Pandas DataFrame to_dict method.
        """
        return self.to_pandas().to_dict(*args, **kwargs)

    def to_hdf(self, *args, **kwargs):
        """
        Write the DataFrame to a Hierarchical Data Format (HDF) file.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_hdf.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_hdf.
        :return: Output of Pandas DataFrame to_hdf method.
        """
        return self.to_pandas().to_hdf(*args, **kwargs)

    def to_markdown(self, *args, **kwargs):
        """
        Convert the DataFrame to a Markdown string.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_markdown.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_markdown.
        :return: Output of Pandas DataFrame to_markdown method.
        """
        return self.to_pandas().to_markdown(*args, **kwargs)

    def to_period(self, *args, **kwargs):
        """
        Convert DataFrame from DatetimeIndex to PeriodIndex.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_period.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_period.
        :return: Output of Pandas DataFrame to_period method.
        """
        return self.to_pandas().to_period(*args, **kwargs)

    def to_stata(self, *args, **kwargs):
        """
        Export the DataFrame to Stata data format.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_stata.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_stata.
        :return: Output of Pandas DataFrame to_stata method.
        """
        return self.to_pandas().to_stata(*args, **kwargs)

    def to_xml(self, *args, **kwargs):
        """
        Convert the DataFrame to an XML string.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_xml.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_xml.
        :return: Output of Pandas DataFrame to_xml method.
        """
        return self.to_pandas().to_xml(*args, **kwargs)

    def to_excel(self, *args, **kwargs):
        """
        Write the DataFrame to an Excel file.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_excel.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_excel.
        :return: Output of Pandas DataFrame to_excel method.
        """
        return self.to_pandas().to_excel(*args, **kwargs)

    def to_html(self, *args, **kwargs):
        """
        Render the DataFrame as an HTML table.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_html.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_html.
        :return: Output of Pandas DataFrame to_html method.
        """
        return self.to_pandas().to_html(*args, **kwargs)

    def to_numpy(self, *args, **kwargs):
        """
        Convert the DataFrame to a NumPy array.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_numpy.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_numpy.
        :return: Output of Pandas DataFrame to_numpy method.
        """
        return self.to_pandas().to_numpy(*args, **kwargs)

    def to_string(self, *args, **kwargs):
        """
        Render the DataFrame to a console-friendly tabular output.

        :param args: Positional arguments to be passed to pandas.DataFrame.to_string.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.to_string.
        :return: Output of Pandas DataFrame to_string method.
        """
        return self.to_pandas().to_string(*args, **kwargs)

    @classmethod
    @property
    def valid_data_types(cls):
        return set([item for key in cls.types for item in cls.types[key]])

    @classmethod
    def from_csv(cls, *args, **kwargs):
        """
        Read a comma-separated values (csv) file into a CustomDataFrame.

        :param args: Positional arguments to be passed to pandas.read_csv.
        :param kwargs: Keyword arguments to be passed to pandas.read_csv.
        :return: A CustomDataFrame object.
        """
        return cls(data=pd.read_csv(*args, **kwargs))

    @classmethod
    def from_dict(cls, data, *args, **kwargs):
        """
        Construct a CustomDataFrame from a dict of array-like or dicts.

        :param data: Dictionary of data.
        :param args: Positional arguments to be passed to pandas.DataFrame.from_dict.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.from_dict.
        :return: A CustomDataFrame object.
        """
        return cls.from_pandas(df=pd.DataFrame.from_dict(data, *args, **kwargs))


    def to_flow(self, interface):
        """
        Writes the output data to the flows specified in the interface.

        :param interface: Interface object.
        """
        if not isinstance(interface, (dict, Interface)):
            raise ValueError("Interface must be a dictionary or of type Interface.")
        data_written = False
        for typ, details in interface.items():
            if typ in self.types["output"]:
                data = self._d.get(typ)
                if data is not None:
                    try:
                        access.io.write_data(data, details)
                        data_written = True
                        log.info(f"Data for type '{typ}' written successfully.")
                    except Exception as e:
                        log.error(f"Error writing data for type '{typ}': {e}")
                else:
                    log.warning(f"No data found for type '{typ}' to write.")
        if not data_written:
            log.warning(f"No data written, implying no data of type \"output\" found, data in CustomDataFrame are \"{', '.join(self._d)}\".")
        
    @classmethod
    def from_flow(cls, interface):
        """
        Construct a CustomDataFrame from a interface object.

        :param interface: Interface object.
        :type interface: lynguine.config.interface.Interface or dict.
        :return: A CustomDataFrame object.
        """

        # TODO: For input, convert this to a simple "read_data" operation
        # and have the merges handled by read_hstack and
        # read_vstack. Make it illegal to do a read_hstack or
        # read_vstack if it's an output.
        if not isinstance(interface, (dict, Interface)):
            raise ValueError("Interface must be a dictionary or of type Interface.")
        default_joins = "outer"
        # Initialize compute from the interface so it can be used below.
        compute = Compute.from_flow(interface)
        cdf = cls({}, compute=compute)
        
        found_data = False
        for key, item in interface.items():
            # Check if the interface key is a valid data key
            if key in cls.valid_data_types: # input, output, cache, parameters
                if "mapping" in item:
                    mapping = item["mapping"]
                else:
                    mapping = []
                if key in cdf._d:
                    raise ValueError(
                        f"Attempting to set the \"{key}\" portion of the data frame from flow, but have found one already exists. Current keys are \"{', '.join(cdf._d.keys())}\"."
                    )
                found_data = True
                if key not in cls.types["input"]: # allow creation of non-inputs if they don't exist
                    if isinstance(item, dict):
                        if access.io.data_exists(item):
                            newdf = cdf._finalize_df(*access.io.read_data(item))
                        else:
                            log.info(f"Data for type '{key}' not found, creating new..")
                            if "columns" in item:
                                columns = item["columns"]
                            else:
                                if key in cls.types["cache"]:
                                    columns = interface.get_cache_columns()
                                elif key in cls.types["output"]:
                                    columns = interface.get_output_columns()
                                else:
                                    raise ValueError(
                                        f"Unrecognised key type \"{key}\". Valid data types are \"{', '.join(cls.valid_data_types)}\"."
                                    )
                            newdf = pd.DataFrame(index=cdf.index, columns=columns)
                            
                    else:
                        raise ValueError(
                            f"Item data descriptions must be in the form of a dictionary unless they are of type \"input\", when a list is valid and implies an \"hstack\" type is needed. The type of item you have provided for the key \"{key}\" is \"{type(item)}\"."
                        )
                else:
                    # if isinstance(item, list):
                    #     # If there's a list, the an hstack is implied.
                    #     log.info(f"Converting input \"{key}\" into an hstack as it's provided as a list.")
                    #     details = {}
                    #     details[key] = {"type" : "hstack", "descriptions" : item}
                    newdf = cdf._finalize_df(*access.io.read_data(item))
                    # elif isinstance(item, dict):
                    #     print(cdf.compute)
                    #     newdf = cdf._finalize_df(*access.io.read_data(item))
                    # print(type(item))

                if key in cls.types["parameters"]:
                    # If select is listed choose only the row of the data frame.
                    if "select" in item:
                        # Select the data from the dataframe.
                        newds = newdf.loc[item["select"]]
                        newdf = newds.to_frame().T
                        
#                        items = [items]
                    # # Iterate through adding the entries.
                    # for item in items:
                    #     newdf = cdf._finalize_df(*access.io.read_data(item))
                    #     # Use join from the item if it's there.
                    #     join = item["how"] if "how" in item else default_joins
                    #     if key in cls.types["parameters"]:
                    #         # If select is listed choose only the row of the data frame.
                    #         if "select" in item:
                    #             # Select the data from the dataframe.
                    #             newds = newdf.loc[item["select"]]
                    #             newdf = newds.to_frame().T
                    #         if key not in cdf._d:
                    #             # Set the series to the new data.
                    #             if cdf.empty:
                    #                 cdf = cls(data=newdf, colspecs={key: list(newdf.columns)})
                    #             else:
                    #                 cdf._d[key] = newdf.iloc[0]
                    #                 cdf._colspecs[key] = list(cdf._d[key].index)
                    #         else:
                    #             # Add augment the series with the new data.
                    #             if cdf.empty:
                    #                 cdf = cls(data=newdf, colspecs={key: list(newdf.columns)})
                    #             else:
                    #                 cdf._d[key] = pd.concat([cdf._d[key], newdf.iloc[0]])
                    #                 cdf._colspecs[key] = list(cdf._d[key].index)
                if cdf.empty:
                    compute = cdf.compute
                    cdf = cls(data=newdf, colspecs={key: list(newdf.columns)})
                    cdf.compute = compute
                else:
                    cdf._d[key] = newdf
                    cdf._colspecs[key] = list(cdf._d[key].columns)
                            # else:
                            #     cdf._d[key] = cdf._d[key].join(newdf, how=join)
                            #     cdf._colspecs[key] = list(cdf._d[key].index)
                if isinstance(mapping, dict):
                    mapping = [mapping]
                               
                for mapp in mapping:
                    for name, column in mapp.items():
                        if column in cdf._d[key]:
                            cdf.update_name_column_map(name, column)
                cdf._augment_column_names(cdf._d[key])
                
        if not found_data:
            errmsg = f'No valid data found in interface. Data fields must be one of "{", ".join(cls.valid_data_types)}"'
            log.error(errmsg)
            raise ValueError(errmsg)
        else:
            cdf.interface = interface

        return cdf
    
    def save_flows(self):
        """
        Save the output flows.
        """
        for typ in self.types["output"]:
            if typ in self._d:
                log.info(f"Saving data for flow type '{typ}'")
                access.io.write_data(self._d[typ], self.interface[typ])
    
    def sort_values(self, *args, inplace=False, **kwargs):
        """
        Sort by the values along either axis.

        :param by: str or list of str
        :param axis: {0 or 'index', 1 or 'columns'}, default 0
        :param ascending: bool or list of bool, default True
        :param inplace: bool, default False
        :param kind: {'quicksort', 'mergesort', 'heapsort'}, default 'quicksort'
        :param na_position: {'first', 'last'}, default 'last'
        :param ignore_index: bool, default False
        :param key: callable, optional
        :return: sorted_obj : CustomDataFrame
        :raises ValueError: If any of the keys are not in the index
        """
        df = self.to_pandas().sort_values(
            *args,
            inplace=False,
            **kwargs,
        )
        if inplace:
            self._distribute_data(df)
        else:
            return self.__class__(
                df,
                colspecs=self.colspecs,
                index=self.get_index(),
                column=self.get_column(),
                selector=self.get_selector(),
            )

    def sort_index(self, *args, inplace=False, **kwargs):
        """
        Sort object by labels (along an axis).

        :param axis: {0 or 'index', 1 or 'columns'}, default 0
        :param level: int or level name or list of ints or list of level names
        :param ascending: bool or list of bool, default True
        :param inplace: bool, default False
        :param kind: {'quicksort', 'mergesort', 'heapsort'}, default 'quicksort'
        :param na_position: {'first', 'last'}, default 'last'
        :param sort_remaining: bool, default True
        :param ignore_index: bool, default False
        :param key: callable, optional.
        :return: sorted_obj : CustomDataFrame
        """
        df = self.to_pandas().sort_index(*args, inplace=False, **kwargs)
        if inplace:
            self._distribute_data(df)
        else:
            return self.__class__(
                df,
                colspecs=self.colspecs,
                index=self.get_index(),
                column=self.get_column(),
                selector=self.get_selector(),
            )

    def convert(self, other):
        """
        Convert various data types to a CustomDataFrame.

        This method handles conversion from different data types like Pandas DataFrame,
        Pandas Series, NumPy array, list, and dictionary to the CustomDataFrame format.

        :param other: The data to be converted.
        :return: A CustomDataFrame object.
        :raises ValueError: If the data type of `other` cannot be converted.
        """

        if isinstance(other, self.__class__):
            # No conversion needed if it's already a CustomDataFrame
            return other

        elif isinstance(other, (pd.DataFrame, pd.Series)):
            # Directly convert from Pandas DataFrame or Series
            return self.__class__(other)

        elif isinstance(other, np.ndarray):
            # Handle NumPy array conversion
            return self._convert_numpy_array(other)

        elif isinstance(other, list):
            # Convert list to CustomDataFrame
            return self.__class__(self._convert_numpy_array(np.array(other)))

        elif isinstance(other, dict):
            # Convert dictionary to CustomDataFrame
            return self.__class__(pd.DataFrame.from_dict(other))

        else:
            # Raise error for unsupported types
            return other

    def _convert_numpy_array(self, array):
        """
        Helper method to convert a NumPy array to a CustomDataFrame.

        This method is called internally to handle specific scenarios based on the shape
        of the NumPy array.

        :param array: The NumPy array to be converted.
        :return: A CustomDataFrame object.
        :raises ValueError: If the array shape is not compatible.
        """

        if array.shape == self.shape:
            # Array shape matches the CustomDataFrame shape
            return self.__class__(
                data=pd.DataFrame(array, index=self.index, columns=self.columns),
            )
        elif len(array.shape) == 1:
            # Single dimensional array (e.g. [1, 2, 3])
            return self.__class__(
                data=pd.DataFrame(array, index=self.index, columns=[self.get_column()]),
            )
        elif array.ndim == 2 and array.shape[0] == 1:
            # Two-dimensional array but with a single row (e.g. [[1, 2, 3]])
            if array.shape[1] != len(self.columns):
                raise ValueError(
                    "NumPy array width doesn't match CustomDataFrame array width."
                )
            return self.__class__(
                data=pd.DataFrame(
                    array,
                    index=[self.get_index()],
                    columns=self.columns,
                ),
            )
        elif array.ndim == 2 and array.shape[1] == 1:
            # Two-dimensional array but with a single column (e.g. [[1], [2], [3]])
            if array.shape[0] != len(self.index):
                raise ValueError(
                    "NumPy array depth doesn't match CustomDataFrame array depth."
                )
            return self.__class__(
                data=pd.DataFrame(
                    array,
                    index=self.index,
                    columns=pd.Index([self.get_column()]),
                ),
            )
        else:
            # Incompatible array shape
            raise ValueError(
                "NumPy array shape is not compatible with CustomDataFrame."
            )

    # Mathematical operations
    def sum(self, axis=0):
        if axis == 0:
            column = self.get_column()
            colspecs = {"parameter_cache": list(self.columns)}
        else:
            column = self.get_index()
            colspecs = {"parameter_cache": list(self.index)}

        return self.__class__(
            data=self.to_pandas().sum(axis),
            colspecs=colspecs,
            column=column,
        )

    def mean(self, axis=0):
        if axis == 0:
            column = self.get_column()
            colspecs = {"parameter_cache": list(self.columns)}
        else:
            column = self.get_index()
            colspecs = {"parameter_cache": list(self.index)}
        return self.__class__(
            data=self.to_pandas().mean(axis),
            colspecs=colspecs,
            column=column,
        )

    def add(self, other):
        other = self.convert(other)
        return self.__class__(
            data=self.to_pandas().add(other.to_pandas()),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def subtract(self, other):
        other = self.convert(other)
        return self.__class__(
            data=self.to_pandas().subtract(other.to_pandas()),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def multiply(self, other):
        other = self.convert(other)
        return self.__class__(
            data=self.to_pandas().multiply(pd.DataFrame(other.to_pandas())),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def equals(self, other):
        other = self.convert(other)
        return self.to_pandas().equals(other.to_pandas())

    def transpose(self):
        return self.__class__(
            self.to_pandas().transpose(),
            index=self.get_column(),
            column=self.get_index(),
            selector=None,
            colspecs="cache",
        )

    def dot(self, other):
        other = self.convert(other)
        return self.__class__(
            self.dot(self.to_pandas(), other.to_pandas()),
            colspecs="cache",
        )

    def isna(self):
        return self.__class__(
            data=self.to_pandas().isna(),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def isnull(self):
        return self.isna()

    def notna(self):
        return ~self.isna()

    def fillna(self, *args, **kwargs):
        return self.__class__(
            data=self.to_pandas().fillna(*args, **kwargs),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def dropna(self):
        vals = self.to_pandas().isna()
        if self.get_index() not in vals.index:
            ind = None
        else:
            ind = self.get_index()

        if self.get_column() not in vals.columns:
            col = None
        else:
            col = self.get_column()

        if self.get_selector() is None or self.get_selector() not in vals.columns:
            sel = None
        else:
            sel = self.get_selector()

        return self.__class__(
            data=vals,
            colspecs=self._colspecs,
            index=ind,
            column=col,
            selector=sel,
        )

    def drop_duplicates(self, *args, **kwargs):
        vals = self.to_pandas().drop_duplicates(*args, **kwargs)
        if self.get_index() not in vals.index:
            index = None
        else:
            index = self.get_index()
        return self.__class__(
            data=vals,
            colspecs=self._colspecs,
            index=index,
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def groupby(self, *args, **kwargs):
        """
        Group DataFrame using a mapper or by a Series of columns.

        :param args: Positional arguments to be passed to pandas.DataFrame.groupby.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.groupby.
        :return: A pd.DataFrameGroupBy object.
        """
        return self.to_pandas().groupby(*args, **kwargs)

    def pivot_table(self, *args, **kwargs):
        """
        Create a pivot table as a CustomDataFrame.

        :param args: Positional arguments to be passed to pandas.DataFrame.pivot_table.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.pivot_table.
        :return: A pivoted CustomDataFrame object.
        """
        return self.__class__(
            data=self.to_pandas().pivot_table(*args, **kwargs),
        )

    def _apply_operator(self, other, operator):
        """
        Apply a specified operator to the DataFrame.

        :param other: The right-hand operand.
        :param operator: The operator function to apply.
        :return: A new instance of CustomDataFrame after applying the operator.
        """
        method = getattr(self.to_pandas(), operator)

        # deal with pandas translation of single row on right to a series.
        if isinstance(other, CustomDataFrame):
            right = other.to_pandas()
        else:
            right = other

        return self.__class__(
            data=method(right),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    @property
    def dtypes(self) -> pd.Series:
        """
        Property to return the data types of the columns across all sub-DataFrames.
        :return: A Series containing the data types of the columns.
        """
        all_dtypes = {}
        for df_name, df in self._d.items():
            if df_name in self.types["parameters"]:
                # the data should be a series
                for col in df.index:
                    all_dtypes[col] = df.dtype
            else:
                for col in df.dtypes.index:
                    all_dtypes[col] = df.dtypes[col]
        return pd.Series(all_dtypes)
    
    @property
    def log(self):
        """
        Access the system log.

        :return: Reference to the system log.
        """
        return self._log

    @log.setter
    def log(self, value):
        """
        Set the system log.

        :param value: The new system log.
        """
        self._log = value
    @property
    def T(self):
        """
        Transpose the DataFrame.

        :return: Transposed CustomDataFrame.
        """
        return self.transpose()

    @property
    def shape(self):
        """
        Return the shape of the DataFrame.

        :return: A tuple representing the DataFrame's dimensions.
        """
        return len(self.index), len(self.columns)

    @property
    def columns(self):
        """
        Return the column labels of the DataFrame.

        :return: Index object containing the column labels.
        """
        columns = []
        for typ, data in self._d.items():
            if typ in self.types["parameters"]:
                columns += list(data.index)
            else:
                columns += list(data.columns)
        return pd.Index(columns)

    @property
    def index(self):
        """
        Return the index (row labels) of the DataFrame.

        :return: Index object containing the row labels.
        """
        # Take index from first entry in _d that is not a "parameters" entry
        # Note that if first entry is a "series" entry, then index will likely be duplicated
        parameters = False
        for typ, data in self._d.items():
            if typ not in self.types["parameters"]:
                return data.index
            else:
                parameters = True
        # If all entries are "parameters" entries, then return single index
        if parameters:
            return pd.Index([0])
        else:
            return pd.Index([])

    @property
    def empty(self):
        """
        Return True if DataFrame is empty.
        """
        return self.to_pandas().empty
    
    @property
    def values(self):
        """
        Return the values of the DataFrame as a NumPy array.

        :return: A NumPy array of the DataFrame's values.
        """
        return self.to_pandas().values

    @property
    def colspecs(self):
        """
        Return the column specifications.

        :return: Column specifications.
        """
        return self._colspecs

    @colspecs.setter
    def colspecs(self, value):
        """
        Set the column specifications.

        :param value: New column specifications.
        """
        self._colspecs = value
        
    @property
    def _data_dictionary(self):
        """
        Return the data dictionary.

        :return: Data dictionary.
        """
        return self._d
    
    # Operators
    def __len__(self):
        """
        Return the number of rows in the CustomDataFrame.

        Overriding the __len__ method allows the use of the len() function
        on the CustomDataFrame, similar to how len() is used with Pandas DataFrame.
        It returns the number of rows in the DataFrame.

        :return: The number of rows in the CustomDataFrame.
        :rtype: int
        """

        # Because we don't return series, length should be the non-singleton dimension.
        return self.shape[0]

    def __add__(self, other):
        """
        Overload the addition ('+') operator.

        :param other: The right-hand operand for addition.
        :return: The result of adding the CustomDataFrame and other.
        """
        return self.add(other)

    def __sub__(self, other):
        """
        Overload the subtraction ('-') operator.

        :param other: The right-hand operand for subtraction.
        :return: The result of subtracting other from the CustomDataFrame.
        """
        return self.subtract(other)

    def __mul__(self, other):
        """
        Overload the multiplication ('*') operator.

        :param other: The right-hand operand for multiplication.
        :return: The result of multiplying the CustomDataFrame and other.
        """
        return self.multiply(other)

    def __invert__(self):
        """
        Overload the bitwise NOT ('~') operator.

        :return: The result of bitwise NOT of the CustomDataFrame.
        """
        return self.__class__(
            data=~self.to_pandas(),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def __neg__(self):
        """
        Overload the unary negation ('-') operator.

        :return: The result of negating the CustomDataFrame.
        """
        return self.__class__(
            data=-self.to_pandas(),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def __truediv__(self, other):
        """
        Overload the true division ('/') operator.

        :param other: The right-hand operand for division.
        :return: The result of true division of the CustomDataFrame by other.
        """
        other = self.convert(other)
        return self.__class__(
            data=self.to_pandas() / other.to_pandas(),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def __floordiv__(self, other):
        """
        Overload the floor division ('//') operator.

        :param other: The right-hand operand for floor division.
        :return: A new instance of CustomDataFrame after floor division.
        """
        other = self.convert(other)
        return self.__class__(
            data=self.to_pandas() // other.to_pandas(),
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def __matmul__(self, other):
        """
        Overload the matrix multiplication ('@') operator.

        :param other: The right-hand operand for matrix multiplication.
        :return: The result of the matrix multiplication.
        """
        return self.dot(other)

    def __pow__(self, exponent):
        """
        Overload the power ('**') operator.

        :param exponent: The exponent to raise the dataframe to.
        :return: A new instance of CustomDataFrame after raising to the power.
        """
        return self.__class__(
            data=self.to_pandas() ** exponent,
            colspecs=self._colspecs,
            index=self.get_index(),
            column=self.get_column(),
            selector=self.get_selector(),
        )

    def __eq__(self, other):
        """
        Overload the equality ('==') operator.

        :param other: The right-hand operand for comparison.
        :return: The result of the equality comparison.
        """
        return self._apply_operator(other, "__eq__")

    def __gt__(self, other):
        """
        Overload the greater than ('>') operator.

        :param other: The right-hand operand for comparison.
        :return: The result of the greater than comparison.
        """
        return self._apply_operator(other, "__gt__")

    def __lt__(self, other):
        """
        Overload the less than ('<') operator.

        :param other: The right-hand operand for comparison.
        :return: The result of the less than comparison.
        """
        return self._apply_operator(other, "__lt__")

    def __ge__(self, other):
        """
        Overload the greater than or equal to ('>=') operator.

        :param other: The right-hand operand for comparison.
        :return: The result of the greater than or equal to comparison.
        """
        return self._apply_operator(other, "__ge__")

    def __le__(self, other):
        """
        Overload the less than or equal to ('<=') operator.

        :param other: The right-hand operand for comparison.
        :return: The result of the less than or equal to comparison.
        """
        return self._apply_operator(other, "__le__")

    def __ne__(self, other):
        """
        Overload the not equal ('!=') operator.

        :param other: The right-hand operand for comparison.
        :return: The result of the not equal comparison.
        """
        return self._apply_operator(other, "__ne__")

    def __array__(self, dtype=None):
        """
        Convert the CustomDataFrame to a NumPy array.

        :param dtype: The desired data-type for the array.
        :return: A NumPy array representation of the CustomDataFrame.
        """
        return np.array(self.to_pandas(), dtype=dtype)

    def __getitem__(self, key):
        """
        Get item or slice from the DataFrame.

        :param key: The key or slice to access elements of the DataFrame.
        :retugrn: A subset of the DataFrame corresponding to the given key.
        """
        if isinstance(key, CustomDataFrame):
            key = key.to_pandas()
        df = self.to_pandas()[key]

        if isinstance(df, pd.Series):
            return df
        else:
            colspecs = {"cache": df.columns}
            return self.__class__(
                data=df,
                colspecs=colspecs,
            )

    def __setitem__(self, key, value):
        raise NotImplementedError("This is a base class")

    def __iter__(self):
        for column in self.columns:
            yield column

    def __str__(self):
        return str(self.to_pandas())

    def __repr__(self):
        return repr(self.to_pandas())

    def _update_colspecs_after_merge(self, right, merged_df, on, suffixes):
        """
        Update colspecs after a merge operation to reflect changes in column names.

        :param left: The left DataFrame used in the merge.
        :param right: The right DataFrame used in the merge.
        :param merged_df: The resulting merged DataFrame.
        :param on: Columns used for merging.
        :param suffixes: Suffixes used in the merge to resolve overlapping column names.
        :return: Updated colspecs dictionary.
        """
        if on is None:
            on = []

        # Initialize updated colspecs
        updated_colspecs = {k: list(v) for k, v in self.colspecs.items()}

        # Add right DataFrame's colspecs, preferring left in case of overlap
        for ctype, cols in right.colspecs.items():
            if ctype in updated_colspecs:
                updated_colspecs[ctype].extend([col for col in cols if col not in on])
            else:
                updated_colspecs[ctype] = [col for col in cols if col not in on]

        # Adjust column names for suffixes and merge keys
        left_suffix, right_suffix = suffixes
        allocated = []
        for ctype, cols in updated_colspecs.items():
            updated = []
            for col in cols:
                if (
                    col in self.columns
                    and col not in on
                    and (col + left_suffix) in merged_df.columns
                    and (col + left_suffix) not in allocated
                ):
                    updated.append(col + left_suffix)
                    allocated.append(col + left_suffix)
                elif (
                    col in right.columns
                    and col not in on
                    and (col + right_suffix) in merged_df.columns
                    and (col + right_suffix) not in allocated
                ):
                    updated.append(col + right_suffix)
                    allocated.append(col + right_suffix)
                else:
                    updated.append(col)
                    allocated.append(col)
            updated_colspecs[ctype] = updated

        # Remove any columns that are not in the merged DataFrame
        for ctype in updated_colspecs:
            updated_colspecs[ctype] = [
                col for col in updated_colspecs[ctype] if col in merged_df.columns
            ]

        return updated_colspecs

    def merge(
        self,
        right,
        how="inner",
        on=None,
        left_on=None,
        right_on=None,
        suffixes=("_x", "_y"),
        *args,
        **kwargs,
    ):
        """
        Merge CustomDataFrame with another DataFrame or CustomDataFrame.

        :param right: Another DataFrame or CustomDataFrame to merge with.
        :param how, on, left_on, right_on, args, kwargs: Parameters for pandas.DataFrame.merge.
        :param suffixes: A tuple of string suffixes to apply to overlapping column names.
        :return: A new CustomDataFrame resulting from the merge operation.
        """
        # Perform the merge operation
        merged_df = pd.merge(
            self.to_pandas(),
            right.to_pandas() if isinstance(right, CustomDataFrame) else right,
            how=how,
            on=on,
            left_on=left_on,
            right_on=right_on,
            suffixes=suffixes,
            *args,
            **kwargs,
        )

        # Update colspecs
        colspecs = self._update_colspecs_after_merge(
            right, merged_df, on=on, suffixes=suffixes
        )

        return self.__class__(merged_df, colspecs=colspecs)

    def join(
            self,
            other,
            on=None,
            how="left",
            lsuffix='',
            rsuffix='',
            sort=False,
            validate=None,
            *args,
            **kwargs,
            ):
        """
        Join CustomDataFrame with another DataFrame or CustomDataFrame.

        :param other: Another DataFrame or CustomDataFrame to merge with.
        :param on: Columns to join on.
        :type on: str, list, or array-like
        :param how: How to join the DataFrames.
        :type how: str
        :param lsuffix: Suffix to apply to overlapping column names from the left DataFrame.
        :type lsuffix: str
        :param rsuffix: Suffix to apply to overlapping column names from the right DataFrame.
        :type rsuffix: str
        :param sort: Sort the join keys lexicographically in the result DataFrame.
        :type sort: bool
        :param args: Positional arguments to be passed to pandas.DataFrame.join.
        :param kwargs: Keyword arguments to be passed to pandas.DataFrame.join.
        :return: A new CustomDataFrame resulting from the join operation.
        """
        # Perform the join operation
        join_df = self.to_pandas().join(
            other=other.to_pandas() if isinstance(other, CustomDataFrame) else other,
            on=on,
            how=how,
            lsuffix=lsuffix,
            rsuffix=rsuffix,
            sort=sort,
            validate=validate,
            *args,
            **kwargs,
        )

        # Update colspecs
        colspecs = self._update_colspecs_after_merge(
            other, join_df, on=on, suffixes=(lsuffix, rsuffix),
        )

        return self.__class__(join_df, colspecs=colspecs)

    def _extract_compute(self, interface : Interface) -> Compute:
        """
        Extract the compute object.

        :param interface: The interface to the compute object.
        :type interface: lynguine.config.interface.Interface or dict
        :returns: The compute object.
        """
        raise NotImplementedError("This is a base class")
                            
    def _finalize_df(self, data, interface):
        """
        This function is used to attend to any modifications in the details dict to finalize the data frame. It fixes up the index, adds columns, sets the right data type etc."""

        raise NotImplementedError("This is a base class")
    
class CustomDataFrame(DataObject):
    types = {
        # Input types are standard DataFrames but are not mutable.
        "input": [
            "input",
            "data",
            "constants",
            "global_consts",
        ],
        # Output types are standard DataFrames that are mutable and
        # intended to be recorded once operations on the
        # CustomDataFrame are complete.
        "output": [
            "output",
            "writedata",
            "writeseries",
            "parameters",
            "globals",
        ],
        # Parameter types do not have an index, they are globally valid.
        "parameters": [
            "constants",
            "global_consts",
            "parameters",
            "globals",
            "parameter_cache",
            "global_cache",
        ],
        # Cache types are standard DataFrames that are mutable and
        # intended to be used for intermediate calculations.
        "cache": [
            "cache",
            "series_cache",
            "parameter_cache",
            "global_cache",
        ],
        # Series types are standard DataFrames that are mutable and
        # may have multiple rows with the same index.
        "series": [
            "series",
            "writeseries",
            "series_cache",
        ],
    }
    def __init__(
            self, data, colspecs=None, index=None, column=None, selector=None, subindex=None, compute=None
    ):
        if data is None:
            data = {}

        # Check if compute is an Interface or a dictionary.
        if compute is None:
            self.compute = Compute({})
        elif isinstance(compute, dict) or isinstance(compute, Interface):
            self.compute = self._extract_compute(compute)
        elif isinstance(compute, Compute):
            self.compute = compute
        else:
            raise ValueError("compute must be an Interface, dict, or Compute object.")
            
        if isinstance(data, dict):
            if len(data) > 0:  # Check that dictionary has contents.
                # Check if all entries are scalar.
                entries = data.values()
                if all(
                    [
                        isinstance(entry, (int, float, str, bool, complex))
                        for entry in entries
                    ]
                ):
                    data = pd.Series(data).to_frame().T
                elif all(
                        [
                        isinstance(entry, (pd.Series, pd.DataFrame))
                        for entry in entries
                    ]
                ):
                    data = pd.concat(data.values(), axis=1)
                    
            data = pd.DataFrame(data)
        if isinstance(data, list):
            data = pd.DataFrame(data)
        if isinstance(data, np.ndarray):
            data = pd.DataFrame(data)
        if isinstance(data, pd.Series):
            data = data.to_frame(name=data.name).T

        self._name_column_map = {}
        self._column_name_map = {}


        # If the colspecs isn't specified assume it's of "cache" type.
        if colspecs is None:
            colspecs = {"cache": list(data.columns)}
        elif isinstance(colspecs, str):
            # Check if colspecs is in any of the types dictionary's entries.
            all_types = [typ for typs in self.types.values() for typ in typs]
            if colspecs in all_types:
                colspecs = {
                    colspecs: list(data.columns),
                }
            else:
                raise ValueError(
                    'Column specification "{colspecs}" not found in types.'
                )

        # Add unspecified columns to cache
        columns = [col for cols in colspecs.values() for col in cols]
        cache = [col for col in data.columns if col not in columns]
        if len(cache) > 0:
            if "cache" not in colspecs:
                colspecs["cache"] = []
            colspecs["cache"] += cache

        self._colspecs = colspecs
        self._d = {}
        self._distribute_data(data)

        self.autocache = True        
        self.interface = Interface({})

        # Set index if not specified
        if index is None:
            indices = self.index
            if len(indices) > 0:
                index = indices[0]
        self.set_index(index)

        # Set column if not specified
        if column is None:
            columns = self.columns
            if len(columns) > 0:
                column = self.columns[0]       
        self.set_column(column)

        self._selector = selector
        # Set selector if not specified
        if self._selector is None:
            selectors = self.get_selectors()
            if len(selectors) > 0:
                self._selector = selectors[0]
        elif selector not in self.get_selectors():
            raise ValueError(
                f"Provided selector '{selector}' not found in CustomDataFrame."
            )

        self._subindex = subindex
        # Set subindex if not specified
        if self._subindex is None:
            subindices = self.get_subindices()
            if len(subindices) > 0:
                self._subindex = subindices[0]
        elif subindex not in self.get_subindices():
            raise ValueError(
                f"Provided subindex '{subindex}' not found in CustomDataFrame."
            )
        
        self.at = self._AtAccessor(self)
        self.loc = self._LocAccessor(self)
        self.iloc = self._ILocAccessor(self)


    @property
    def compute(self):
        """
        Return the compute object.

        :return: The compute object.
        :rtype: Compute
        """
        return self._compute

    @compute.setter
    def compute(self, value):
        """
        Set the compute object.

        :param value: The compute object.
        :type value: Compute
        :return: None
        """
        self._compute = value
        
    class _AtAccessor:
        def __init__(self, data):
            """
            Initialize the AtAccessor.

            :param data: The custom DataFrame object to which this accessor is attached.
            """
            self._data_object = data

        def __getitem__(self, key):
            """
            Retrieve a single element from the CustomDataFrame using label-based indexing.

            This method provides access to a single element, similar to pandas' .at accessor.
            It expects a single label for both row and column.

            :param key: A tuple containing the row and column label.
            :return: The element at the specified row and column location.
            :raises KeyError: If the specified key is not a tuple or if it does not correspond to a valid row and column label.
            """
            if not isinstance(key, tuple) or len(key) != 2:
                raise KeyError("Key must be a tuple of (row_label, col_label)")

            row_label, col_label = key

            # Logic to handle different data types within the custom DataFrame
            for typ, data in self._data_object._d.items():
                if row_label in data.index and col_label in data.columns:
                    return data.at[row_label, col_label]
                elif typ in self._data_object.types["parameters"]:
                    if col_label in data.index:
                        return data.at[col_label]

            raise KeyError(f"Key {key} not found in the CustomDataFrame")

        def __setitem__(self, key, value):
            """
            Set a single element in the CustomDataFrame using label-based indexing.

            This method provides a way to set the value of a single element, similar to pandas' .at accessor.
            It expects a single label for both row and column and updates the value at that location.

            :param key: A tuple containing the row and column label.
            :param value: The new value to set at the specified location.
            :raises KeyError: If the specified key is not a tuple or if it does not correspond
                              to a valid row and column label.
            """
            if not isinstance(key, tuple) or len(key) != 2:
                raise KeyError("Key must be a tuple of (row_label, col_label)")

            row_label, col_label = key

            # Check for immutable 'input' type columns
            immutable_columns = [
                col
                for typ in self._data_object.types["input"]
                for col in self._data_object.colspecs.get(typ, [])
            ]
            if col_label in immutable_columns:
                raise KeyError(
                    f"Column '{col_label}' is immutable and cannot be modified."
                )

            # Setting the value
            data_modified = False
            for typ, data in self._data_object._d.items():
                if row_label in data.index and col_label in data.columns:
                    data.at[row_label, col_label] = value
                    data_modified = True
                    break
                elif typ in self._data_object.types["parameters"]:
                    if col_label in data.index:
                        raise KeyError(
                            f"Cannot modify individual elements in 'parameters' type data."
                        )

            if not data_modified:
                raise KeyError(f"Key {key} not found in the CustomDataFrame")

            # Update the data object with the modified data
            self._data_object._d[typ] = data

    class _LocAccessor(Accessor):
        def __init__(self, data):
            """
            Initialize the LocAccessor.

            :param data: The custom DataFrame object to which this accessor is attached.
            """
            self._data_object = data

        def __getitem__(self, key):
            """
            Retrieve a subset of the CustomDataFrame based on the provided key.

            This method supports both row and column indexing, similar to pandas' .loc accessor.
            It handles 'parameters' data differently from regular data.

            :param key: The indexing key, which can be a scalar, slice, list, tuple, or pd.Index.
                        It can be a tuple (row_key, col_key) for row and column indexing.
            :return: A subset of the CustomDataFrame as specified by the key.
            """
            # Determine row_key and col_key based on whether key is a tuple
            if isinstance(key, tuple):
                row_key, col_key = key
            else:
                row_key = key
                col_key = slice(None)  # Equivalent to selecting all columns

            colspecs = {}
            # check if index is a datetime index.
            if isinstance(self._data_object.index, pd.DatetimeIndex):
                # if so, allow pandas to handle the slicing.
                ind = self._data_object.to_pandas().loc[row_key].index
                result_df = pd.DataFrame(index=ind, data=None).astype("object")
            elif isinstance(row_key, (list, tuple, pd.Index)):
                # if not, check if the row_key is a list of indices.
                # if so, create a new dataframe with the index of the row_key.
                result_df = pd.DataFrame(index=row_key, data=None).astype("object")
            else:
                # create a data series to handle the result with index.name given by row
                result_df = pd.Series(name=row_key, data=None).astype("object")

            for typ, data in self._data_object._d.items():
                if data.empty:
                    continue

                # Check if col_key is a scalar and convert to list if necessary
                if not isinstance(col_key, (list, tuple, slice, pd.Index)):
                    col_key = [col_key]

                # Handle "parameters" data
                if typ in self._data_object.types["parameters"]:
                    selected_cols = (
                        [col for col in col_key if col in data.index]
                        if isinstance(col_key, (list, tuple, pd.Index))
                        else data.index
                    )
                    for col in selected_cols:
                        result_df[col] = data[col]
                    
                    colspecs[typ] = selected_cols
                else:
                    # Handle regular data
                    filtered_cols = (
                        [col for col in col_key if col in data.columns]
                        if isinstance(col_key, (list, tuple, pd.Index))
                        else data.columns
                    )
                    selected_data = data.loc[row_key, filtered_cols]
                    if isinstance(selected_data, pd.Series):
                        if not isinstance(result_df, pd.Series):
                            raise ValueError(f"The selected data has a row key \"{row_key}\" that has induced a series, but the result_df is of type \"{type(result_df)}\"")
                        # Concatenate the two data series
                        if result_df.empty:
                            result_df = pd.concat([selected_data])
                        elif not selected_data.empty:
                            result_df = pd.concat([result_df, selected_data])
                    else:
                        result_df = result_df.join(selected_data, how="outer")
                    colspecs[typ] = filtered_cols

            # Find empty colspecs
            del_types = []
            for typ in colspecs:
                if len(colspecs[typ]) == 0:
                    del_types.append(typ)

            # Delete empty colspecs
            for typ in del_types:
                del colspecs[typ]

            return self._data_object.__class__(result_df, colspecs=colspecs)

        def __setitem__(self, key, value):
            """
            Set values in the CustomDataFrame based on the provided key.

            This method supports both row and column indexing. It raises an error if attempting
            to modify immutable 'input' type columns.

            :param key: The indexing key, similar to pandas .loc accessor.
            :param value: The value to set at the specified key location.
            :raises KeyError: If attempting to modify immutable 'input' type columns.
            :raises ValueError: If provided values for 'parameters' type data are not identical.
            """
            # Determine row_key and col_key based on whether key is a tuple
            if isinstance(key, tuple):
                row_key, col_key = key
            else:
                row_key = key
                col_key = slice(None)  # Equivalent to selecting all columns

            # Extract the list of immutable columns from colspecs based on types["input"]
            immutable_types = self._data_object.types["input"]
            immutable_columns = [
                col
                for typ in immutable_types
                for col in self._data_object.colspecs.get(typ, [])
            ]

            # Check if any of the columns being modified are immutable
            if isinstance(col_key, (list, tuple, pd.Index)):
                if any(col in immutable_columns for col in col_key):
                    raise KeyError(
                        f"Attempted to modify one or more immutable 'input' type columns when you tried to modify columns \"{col_key}\"."
                    )
            elif col_key in immutable_columns:
                raise KeyError(
                    f"Attempted to modify an immutable 'input' type column when you tried to modify column \"{col_key}\"."
                )

            # Setting values
            for typ, data in self._data_object._d.items():
                if data.empty:
                    continue

                # Check if col_key is a scalar and convert to list if necessary
                if not isinstance(col_key, (list, tuple, slice, pd.Index)):
                    col_key = [col_key]

                # Select the relevant columns
                rel_col = [
                    col for col in col_key if col in self._data_object.colspecs[typ]
                ]
                if len(rel_col) == 0:
                    continue

                if typ in self._data_object.types["parameters"]:
                    # Ensure that provided values for 'parameters' are identical across all rows
                    for col in rel_col:
                        if isinstance(value, pd.DataFrame) and not all(
                            value[col].iloc[0] == v for v in value[col]
                        ):
                            raise ValueError(
                                "Non-identical values provided for 'parameters' type data"
                            )
                        elif not all(value[0] == v for v in value):
                            raise ValueError(
                                "Non-identical values provided for 'parameters' type data"
                            )

                        # Setting values for 'parameters' type data
                        data[col] = (
                            value[col].iloc[0]
                            if isinstance(value, pd.DataFrame)
                            else value
                        )
                else:
                    # Handle setting values for regular data
                    selected_cols = [col for col in col_key if col in data.columns]
                    if len(selected_cols) > 0:
                        data.loc[row_key, selected_cols] = value

                # Update the data object with the modified data
                self._data_object._d[typ] = data

    class _ILocAccessor(Accessor):
        def __init__(self, data):
            """
            Initialize the ILocAccessor.

            :param data: The custom DataFrame object to which this accessor is attached.
            """
            self._data_object = data

        def __getitem__(self, key):
            """
            Retrieve a subset of the CustomDataFrame based on integer-location based indexing.

            This method provides integer-location based indexing, similar to pandas' .iloc accessor.
            It internally converts integer indices to labels and then uses the .loc accessor.

            :param key: The indexing key, which can be an integer, slice, list, or tuple for
                        both rows and columns.
            :return: A subset of the CustomDataFrame as specified by the integer-location key.
            :raises IndexError: If the specified key is not a tuple or if it does not correspond
            """
            # Convert integer indices to labels for rows and columns
            row_labels, col_labels = self._ikey_to_labels(key)

            # Use .loc accessor with label-based keys
            return self._data_object.loc[row_labels, col_labels]

        def __setitem__(self, key, value):
            """
            Set values in the CustomDataFrame based on integer-location based indexing.

            This method provides integer-location based indexing, similar to pandas' .iloc accessor.

            :param key: The indexing key, which can be an integer, slice, list, or tuple for
                        both rows and columns.
            :param value: The value to set at the specified key location.
            """

            # Convert integer indices to labels for rows and columns
            row_labels, col_labels = self._ikey_to_labels(key)

            self._data_object.loc[row_labels, col_labels] = value

        def _ikey_to_labels(self, key):
            """
            Convert integer-location indices to label-based indices.

            :param key: The integer-location based index or slice.
            :return: Label-based indices corresponding to the integer-location key.
            """
            if isinstance(key, tuple):
                row_key, col_key = key
                row_labels = self._convert_to_labels(row_key, self._data_object.index)
                col_labels = self._convert_to_labels(col_key, self._data_object.columns)
            else:
                row_labels = self._convert_to_labels(key, self._data_object.index)
                col_labels = slice(None)  # Select all columns

            return row_labels, col_labels

        def _convert_to_labels(self, key, labels):
            """
            Convert integer-location indices to label-based indices.

            :param key: The integer-location based index or slice.
            :param labels: The index or columns of the DataFrame from which to extract labels.
            :return: Label-based indices corresponding to the integer-location key.
            """
            if isinstance(key, slice):
                # Convert slice of integer indices to labels
                return labels[key]
            elif isinstance(key, (list, int)):
                # Convert list or single integer index to labels
                return labels[key]
            else:
                raise KeyError("Invalid index type for iloc indexing")

    def _distribute_data(self, data):
        """
        Distribute input data according to the colspec.

        :param data: The input data to be distributed.
        :raises ValueError: If the data passed isn't pandas or custom DataFrame
        :raises ValueError: If a parameter column doesn't contain the same values.
        """
        # Distribute data across names columns
        if not isinstance(data, (pd.DataFrame, self.__class__)):
            raise ValueError("Data must be a pandas DataFrame or a custom data frame.")

        for typ, cols in self._colspecs.items():
            if typ in self.types["parameters"]:
                self._d[typ] = pd.Series(index=cols, data=None).astype(object)
                for col in cols:
                    if all(data[col] == data[col].iloc[0]):
                        self._d[typ][col] = data[col].iloc[0]
                    # Check if the column is all NaN/None and the value is NaN.
                    elif all(data[col].isna()) and np.isnan(data[col].iloc[0]):
                        self._d[typ][col] = data[col].iloc[0]
                    else:
                        raise ValueError(
                            f'Column "{col}" is specified as a parameter column and yet the values of the column are not all the same.'
                        )
            else:
                d = data[cols]
                if typ in self.types["series"]:
                    self._d[typ] = d
                else:
                    # If it's not a series type make sure it's deduplicated.
                    if d.index.has_duplicates:
                        log.debug(
                            'Removing duplicated elements from "{typ}" loaded data.'
                        )
                        self._d[typ] = d[~d.index.duplicated(keep="first")]
                    else:
                        self._d[typ] = d

    def to_pandas(self):
        """
        Convert the CustomDataFrame to a pandas DataFrame.

        :return: A pandas DataFrame representation of the CustomDataFrame.
        :rtype: pandas.DataFrame
        """
        df1 = None
        for typ, data in self._d.items():
            if typ in self.types["parameters"]:
                if df1 is None:
                    ind = data.index.name if data.index.name is not None else 0
                    df1 = pd.DataFrame(index=self.index)
                df1 = df1.assign(**data)
            else:
                if df1 is None:
                    df1 = data
                else:
                    df1 = df1.join(data, how="outer")
        return df1

    def from_pandas(self, df, inplace=False):
        """
        Convert from a pandas data frame to a CustomDataFrame.

        :param df: A pandas DataFrame to convert to a CustomDataFrame.
        :param inplace: Whether to perform the conversion in-place or return a new CustomDataFrame.
        :return: A new CustomDataFrame if inplace is False, otherwise None.
        """
        if inplace:
            self._distribute_data(df)
        else:
            return self.__class__(
                df,
                self._colspecs,
                self.get_selector(),
                self.get_index(),
                self.get_column(),
            )

    def filter(self, *args, **kwargs):
        return self.from_pandas(self.to_pandas().filter(*args, **kwargs))

    def _extract_compute(self, interface : Interface) -> Compute:
        """
        Extract the compute object.

        :param interface: The interface to the compute object.
        :type interface: lynguine.config.interface.Interface or dict
        :returns: The compute object.
        """
        return Compute.from_flow(interface).computes
    
    def _finalize_df(self, df : "CustomDataFrame", interface : Interface, strict_columns=False) -> "CustomDataFrame":
        """
        This function augments the raw data and sets the index of the data frame.
        :param df: The data frame to be augmented.
        :param interface: The details of the data frame.
        :param strict_columns: Whether to enforce strict columns.
        :return: The augmented data frame.
        """
        

        if "mapping" in interface:
            
            for name, column in interface["mapping"].items():
                self.update_name_column_map(column=column, name=name)

               
        self._augment_column_names(df)


        
        if "index" not in interface:
            errmsg = f"Missing index field in data frame specification in interface file"
            log.error(errmsg)
            raise ValueError(errmsg)

        if not isinstance(interface["index"], str):
            errmsg = f'"index" should be a string in interface.'
            log.error(errmsg)
            raise ValueError(errmsg)

        index_column_name = interface["index"]
        
        if "columns" in interface:
            # Make sure the listed columns are present.
            for column in interface["columns"]:
                if column not in df.columns:
                    df[column] = None
            if strict_columns:
                if "columns" not in interface:
                    errmsg = f"You can't have strict_columns set to True and not list the columns in the interface structure."
                    log.error(errmsg)
                    raise ValueError(errmsg)
                
                for column in df.columns:
                    if column not in interface["columns"] and column!=index_column_name:
                        errmsg = f"DataFrame contains column: \"{column}\" which is not in the columns list of the specification and strict_columns is set to True."
                        log.error(errmsg)
                        raise ValueError(errmsg)
        if "compute" in interface:
            compute = Compute.from_flow(interface)
            for comp in compute.computes:
                compute_prep = compute.prep(comp, self)
                fargs = compute_prep["args"]
                if "field" in comp: # if field is in compute, then we are computing or updating a new field
                    for ind in df.index:
                        df.loc[ind, comp["field"]] = compute_prep["function"](df.loc[ind], **fargs)

                else:
                    errmsg = f"Compute object in interface file is missing field key."
                    log.error(errmsg)
                    raise ValueError(errmsg)
            
        if index_column_name in df.columns:
            index = pd.Index(df[index_column_name], name=index_column_name)
            df.set_index(index, inplace=True)
            del df[index_column_name]            
                    
        return df

    def _augment_column_names(self, data):
        """
        Add each column name to the column name map if not already there.
        """
        if isinstance(data, pd.Series): # if data is a series, likely its a parameter and its index is equivalent to columns
            columns = data.index 
        else:
            columns = data.columns
        for column in columns:
            # If column title is valid variable name, add it to the column name map
            if column not in self._column_name_map:
                if is_valid_var(column):
                    self.update_name_column_map(name=column, column=column)
                else:
                    name = to_camel_case(column)
                    # Keep variable names as private
                    if name == "_":
                        name = "_" + name

                    log.warning(f"Column \"{column}\" is not a valid variable name and there is no mapping entry to provide an alternative. Auto-generating a mapping entry \"{name}\" to provide a valid variable name to use as proxy for \"{column}\".")
                    if is_valid_var(name):
                        self.update_name_column_map(name=name, column=column)
                    else:
                        errmsg = f"Column \"{column}\" is not a valid variable name. Tried autogenerating a camel case name \"{name}\" but it is also not valid. Please add a mapping entry to provide an alternative to use as proxy for \"{column}\"."
                        log.error(errmsg)
                        raise ValueError(errmsg)
    
    
    def update_name_column_map(self, name, column):
        """
        Update the map from valid variable names to columns in the data frame. Valid variable names are needed e.g. for Liquid filters.

        :param name: The name of the variable.
        :type name: str
        :param column: The column in the data frame.
        :type column: str
        """
        if column in self._column_name_map and self._column_name_map[column] != name:
            original_name = self._column_name_map[column]
            errmsg = f"Column \"{column}\" already exists in the name-column map and there's an attempt to update its value to \"{name}\" when it's original value was \"{original_name}\" and that would lead to unexpected behaviours. Try looking to see if you're setting column values to different names across different files and/or file loaders."
            log.error(errmsg)
            raise ValueError(errmsg)
        self._name_column_map[name] = column
        self._column_name_map[column] = name
        
    def _default_mapping(self):
        """
        Generate the default mapping from config or from columns

        :returns: dictionary of mapping between variable names and column values
        :rtype: dict
        """
        return self._name_column_map

    def mapping(self, mapping=None, series=None):
        """
        Generate dictionary of mapping between variable names and column values.

        :param mapping: mapping to use, if None use default mapping
        :param series: series to use, if None use current series
        :returns: dictionary of mapping between variable names and column values
        :rtype: dict
        """
        
        if mapping is None:
            if series is None: # remove any columns not in self.columns
                mapping = {name: column for name, column in self._default_mapping().items() if column in self.columns or column==self.index.name}
            else: # remove any columns not in provided series
                mapping = {name: column for name, column in self._default_mapping().items() if column in series.index}

        format = {}
        for name, column in mapping.items():
            if series is None:
                self.set_column(column)
                format[name] = self.get_value()
            else:
                if column in series:
                    format[name] = series[column]
        return remove_nan(format)

    def viewer_to_value(self, viewer, kwargs=None):
        """
        Convert a viewer structure to populated values.

        :param viewer: The viewer to create the text of.
        :type viewer: dict or list of dicts
        :param kwargs: The mapping to use to populate the viewer.
        :type kwargs: dict
        :returns: The text of the viewer.
        """
        value = ""
        if type(viewer) is not list:
            viewer = [viewer]
        for view in viewer:
            value += self.view_to_value(view, kwargs)
            if value != "":
                value += "\n\n"
        return value

    def view_to_value(self, view, kwargs=None, local={}):
        """
        Create the text of the view.

        :param view: The view to create the text of.
        :type view: dict
        :param kwargs: The mapping to use to populate the view.
        :type kwargs: dict
        :returns: The text of the view.
        """
        # Ensure view is a dictionary or an Interface
        if isinstance(view, Interface):
            view = view.to_dict()
        elif not isinstance(view, dict):
            raise TypeError("View should be a \"dict\" or an \"Interface\".")

        if self.conditions(view):
            if "local" in view:
                local.update(view["local"])
            if "list" in view:
                values = []
                for v in view["list"]:
                    values.append(self.view_to_value(v, kwargs, local))
                return values
            if "field" in view:
                return self.get_value_column(view["field"])
            if "join" in view:
                if "list" not in view["join"]:
                    log.warning("No field \"list\" in \"concat\" viewer.")
                elements = self.view_to_value(view["join"], kwargs, local)
                if "separator" in view["join"]:
                    sep = view["join"]["separator"]
                else:
                    sep = "\n\n"
                return sep.join(elements)
            if "compute" in view:
                return self.compute_to_value(view["compute"])
            if "liquid" in view:
                return self.liquid_to_value(view["liquid"], kwargs, local)
            if "tally" in view:
                return self.tally_to_value(view["tally"], kwargs, local)
            if "display" in view:
                return self.display_to_value(view["display"], kwargs, local)
            raise KeyError("View needs to contain a key which is one of \"list\", \"field\", \"join\", \"compute\", \"liquid\", \"tally\", or \"display\".")
        
    def summary_viewer_to_value(self, viewer, kwargs=None):
        """
        Convert a summary viewer structure to populated values.

        :param viewer: The summary viewer to create the text of.
        :type viewer: dict or list of dicts
        :param kwargs: The mapping to use to populate the summary viewer.
        :type kwargs: dict
        :returns: The text of the summary viewer.
        """
        value = ""
        if type(viewer) is not list:
            viewer = [viewer]
        for view in viewer:
            value += self.summary_view_to_value(view, kwargs)
            if value != "":
                value += "\n\n"
        return value
    
    def summary_view_to_value(self, view, kwargs=None, local={}):
        """
        Create the text of the summary view.

        :param view: The summary view to create the text of.
        :type view: dict
        :param kwargs: The mapping to use to populate the summary view.
        :type kwargs: dict
        :returns: The text of the summary view.
        """
        # Ensure view is a dictionary or an Interface
        if isinstance(view, Interface):
            view = view.to_dict()
        elif not isinstance(view, dict):
            raise TypeError("View should be a \"dict\" or an \"Interface\".")
        value = ""
        if self.conditions(view):
            if "list" in view:
                values = []
                for v in view["list"]:
                    values.append(self.view_to_value(v, kwargs, local))
                return values
            if "join" in view:
                if "list" not in view["join"]:
                    log.warning("No field \"list\" in \"concat\" viewer.")
                elements = self.view_to_value(view["join"], kwargs)
                if "separator" in view["join"]:
                    sep = view["join"]["separator"]
                else:
                    sep = "\n\n"
                return sep.join(elements)
            if "field" in view:
                value += self.get_value_column(view["field"])
            if "compute" in view:
                value += self.compute_to_value(view["compute"], kwargs, local)
            if "liquid" in view:
                value += self.liquid_to_value(view["liquid"], kwargs, local)
            if "tally" in view:
                value += self.tally_to_value(view["tally"], kwargs, local)
            if "display" in view:
                value += self.display_to_value(view["display"], kwargs, local)
            return value
        else:
            return None

    def view_to_tmpname(self, view):
        """
        Convert a view to a name

        :param view: The view to convert to a name.
        :type view: dict
        :returns: A name derived from the view./
        :rtype: str
        """
        if "list" in view:
            name = "list_"
            for v in view["list"]:
                name += self.view_to_tmpname(v)
                name += "_"
            return name
        elif "field" in view:
            return to_camel_case(view["field"])
        elif "join" in view:
            name = "join_"
            if "list" not in view["join"]:
                log.warning("No field \"list\" in \"concat\" viewer.")
            name += self.view_to_tmpname(view["join"])
            return name
        elif "compute" in view:
            return self.compute_to_tmpname(view["compute"])
        elif "liquid" in view:
            return self.liquid_to_tmpname(view["liquid"])
        elif "display" in view:
            return self.display_to_tmpname(view["display"])

    def tally_to_value(self, tally, kwargs=None, local={}):
        """
        Create the text of the view.

        :param tally: The tally to create the text of.
        :type tally: dict
        :param kwargs: The mapping to use to populate the tally.
        :type kwargs: dict
        :returns: The text of the tally.
        
        """
        return self.tally_values(tally, kwargs, local)

    def tally_to_tmpname(self, tally) -> str:
        """
        Convert a view to a temporary name

        :param tally: The tally to convert to a name.
        :type tally: dict
        :returns: A name derived from the tally.
        :rtype: str
        """
        if "tally" in view:
            name = self.tally_to_tmpname(view["tally"])
        return name

    def conditions(self, view) -> bool:
        """
        Check if a given data viewer should be displayed.

        :param view: The data viewer to check.
        :type view: dict or Interface
        :returns: True if the data viewer should be displayed, False otherwise.
        :rtype: bool
        """
        if "conditions" not in view:
            return True
        else:
            for condition in view["conditions"]:
                if "present" in condition:
                    if not condition["present"]["field"] in self.columns:
                        return False
                    else:
                        self.set_column(condition["present"]["field"])
                        if pd.isna(self.get_value()):
                            return False
                        else:
                            return True

                if "equal" in condition:
                    self.set_column(condition["equal"]["field"])
                    if not self.get_value() == condition["equal"]["value"]:
                        return False
        return True

    def display_to_tmpname(self, display) -> str:
        """
        Convert a display string to a temp name

        :param display: The display string to convert.
        :type display: str
        :returns: A name derived from the display string.
        :rtype: str
        """
        return to_camel_case(display.replace("/", "_").replace("{","").replace("}", ""))


    def display_to_value(self, display, kwargs=None, local={}):
        """
        Convert a display string to a string.

        :param display: The display string to convert.
        :type display: str
        :param kwargs: The mapping to use for the display string, defaults to None
        :type kwargs: dict, optional
        :param local: Local overrides to use on top of the kwargs for substitution in the display string, defaults to {}
        :type local: dict, optional
        :returns: The string extracted from the display string.
        :rtype: str
        :raises KeyError: If the mapping doesn't contain the key requested in the display string.
        """
        if kwargs is None:
            kwargs = self.mapping()
        kwargs.update(local)
        try:
            return display.format(**kwargs)
        except KeyError as err:
            raise KeyError(f"The mapping doesn't contain the key {err} requested in \"{display}\". Set the mapping in \"_referia.yml\".") from err

    def compute_to_value(self, compute):
        """
        Extract a value from a computation

        :param compute: The interface details containing the computation to extract the value from.
        :type compute: dict or Interface
        :returns: The value extracted from the computation.
        """
        compute_prep = self.compute.prep(compute)
        return self.compute.run(compute_prep)
    
    def compute_to_tmpname(self, compute) -> str:
        """
        Convert a compute specification to a descriptive name

        :param compute: The compute specification to convert to a name.
        :type compute: dict or Interface
        :returns: A name derived from the compute specification.
        :rtype: str
        
        """
        return to_camel_case(compute["function"].replace("/", "_").replace("{","").replace("}", "").replace("%","-"))
        
    def liquid_to_tmpname(self, display):
        """
        Convert a liquid template specification to a decriptive name.

        :param display: The liquid template specification to convert to a name.
        :type display: str
        :returns: A name derived from the liquid template specification.
        :rtype: str
        """
        return to_camel_case(display.replace("/", "_").replace("{","").replace("}", "").replace("%","-"))

    
    def liquid_to_value(self, display, kwargs=None, local={}):
        """
        Convert a liquid template to a string.

        :param display: The liquid template to convert.
        :type display: str
        :param kwargs: The mapping to use for the liquid template, defaults to None
        :type kwargs: dict, optional
        :param local: Local overrides to use on top of the kwargs for substitution in the liquid template, defaults to {}
        :type local: dict, optional
        """
        if self.compute is None:
            errmsg = f"Compute needs to be initialised before liquid_to_value is called."
            log.error(errmsg)
            raise ValueError(errmsg)

        if kwargs is None or kwargs=={}:
            kwargs = self.mapping()
        kwargs.update(local)
        try:
            return self.compute._liquid_env.from_string(display).render(**remove_nan(kwargs))
        except Exception as err:
            raise Exception(f"In {display}\n\n {err}") from err

    def tally_to_tmpname(self, tally):
        """Convert a tally to a temporary name"""
        tmpname = ""
        if "begin" in tally:
            tmpname += "begin_"
            tmpname += self.view_to_tmpname(tally["begin"])
        tmpname += "display_"
        tmpname += self.view_to_tmpname(tally)
        if "end" in tally:
            tmpname += "end_"
            tmpname += self.view_to_tmpname(tally["end"])
        return tmpname

    def tally_values(self, tally, kwargs=None, local={}):
        """
        Create the text of the tally. A tally has a "begin" field, and an "end" field and is used for summarising a series.

        :param tally: The tally to create the text of.
        :type tally: dict
        :param kwargs: The mapping to use to populate the tally.
        :type kwargs: dict
        :returns: The text of the tally.
        """
        value = ""
        if "begin" in tally:
            value += tally["begin"]
            if value != "":
                value += "\n\n"
        orig_subindex = self.get_subindex()
        subindices = self.tally_series(tally)
        for subindex in subindices:
            self.set_subindex(subindex)
            value += self.view_to_value(tally, kwargs, local)
            if value != "":
                value += "\n\n"
        self.set_subindex(orig_subindex)
        if "end" in tally:
            value += tally["end"]
            if value != "":
                value += "\n\n"
        return value

    def tally_series(self, tally):
        """
        Return the series to be used for a tally.

        :param tally: The tally to create the text of.
        :type tally: dict
        :returns: The series to be used for a tally.
        :rtype: pd.Series
        
        """
        orig_subindex = self.get_subindex()
        subindices = self.get_subindices()
        if subindices is None:
            return None
        if orig_subindex in subindices:
            cur_loc = subindices.get_loc(orig_subindex)
        else:
            cur_loc = 0
            orig_subindex = subindices[0]
        def subind_val(ind):
            try:
                return pd.Index([subindices[ind]], dtype=subindices.dtypegg)
            except IndexError as e:
                log.warning(f"Requested invalid index in Data.tally_series()")
                return pd.Index([subindices[cur_loc]], dtype=subindices.dtype)

        def subind_series(ind, starter=True, reverse=False):
            try:
                if starter:
                    return pd.Index(subindices[ind:], dtype=subindices.dtype)
                else:
                    return pd.Index(subindices[:ind], dtype=subindices.dtype)

            except IndexError as e:
                log.warning(f"Requested invalid index in Data.tally_series()")
                if starter:
                    return pd.Index(subindices[cur_loc:], dtype=subindices.dtype)
                else:
                    return pd.Index(subindices[:cur_loc], dtype=subindices.dtype)

        if "reverse" not in tally or not tally["reverse"]:
            reverse=False
        else:
            reverse=True
            
        if "which" not in tally:
            return subindices
        elif tally["which"] == "pop":
            return subind_val(0, reverse=reverse)
        elif tally["which"] == "bottom":
            return subind_val(-1, reverse=reverse)
        elif tally["which"] == "previous":
            return subind_val(cur_loc+1, reverse=reverse)
        elif tally["which"] == "next":
            return subind_val(cur_loc-1, reverse=reverse)
        elif tally["which"] == "earlier":
            return subind_series(cur_loc+1, reverse=reverse)
        elif tally["which"] == "later":
            return subind_series(cur_loc, starter=False, reverse=reverse)
        elif tally["which"] == "others":
            return subind_series(cur_loc, starter=False, reverse=reverse).append(subind_series(cur_loc+1))
        elif tally["which"] == "all":
            return subindices
        else:
            errmsg = "Unrecognised subindices specifier in tally."
            log.error(errmsg)
            raise ValueError(errmsg)
    
def concat(objs, *args, **kwargs):
    """
    Concatenate a sequence of CustomDataFrame objects into a single CustomDataFrame.

    :param objs: A sequence of CustomDataFrame objects to concatenate.
    :param args: Positional arguments to be passed to pandas.concat.
    :param kwargs: Keyword arguments to be passed to pandas.concat.
    :return: A new CustomDataFrame representing the concatenation of the input dataframes.
    :raises ValueError: If objs is empty or contains non-CustomDataFrame objects.
    """
    # TK If there are matching indices in the concatenation, need to trigger series in result.
    # Check for empty or invalid inputs
    if not objs or any(not isinstance(obj, CustomDataFrame) for obj in objs):
        raise ValueError("objs must be a non-empty list of CustomDataFrame objects.")

    # Concatenate the dataframes
    df = pd.concat([obj.to_pandas() for obj in objs], *args, **kwargs)

    # Check if df has duplicated index.
    if df.index.has_duplicates:
        colspecs = "series_cache"
    else:
        colspecs = "cache"

    # Handle types - assuming a consistent approach is defined
    # This needs to be decided based on how types are to be handled

    return objs[0].__class__(df, colspecs=colspecs)


