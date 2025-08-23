import pandas as pd
import io
import re
from datetime import datetime

def parse_sql_result_to_dataframe(sql_query, result_data):
    """
    Parse SQL query result into a properly formatted DataFrame
    
    Args:
        sql_query (str): The SQL query that was executed
        result_data: The raw result from database execution
        
    Returns:
        pd.DataFrame: Formatted DataFrame with proper columns and rows
    """
    try:
        # Convert result to string for processing
        result_str = str(result_data).strip()
        
        # Handle empty results
        if not result_str or result_str in ['', '[]', 'None']:
            # Extract column names from SQL SELECT statement
            columns = extract_columns_from_sql(sql_query)
            return pd.DataFrame(columns=columns)
        
        # Method 1: Try to parse if result looks like a list of tuples
        if result_str.startswith('[') and result_str.endswith(']'):
            try:
                # Use eval carefully - in production, consider using ast.literal_eval
                parsed_result = eval(result_str)
                if isinstance(parsed_result, list) and parsed_result:
                    # Extract columns from SQL
                    columns = extract_columns_from_sql(sql_query)
                    
                    # Handle single row result
                    if isinstance(parsed_result[0], (tuple, list)):
                        return pd.DataFrame(parsed_result, columns=columns)
                    else:
                        # Single value result
                        return pd.DataFrame([parsed_result], columns=columns)
            except:
                pass
        
        # Method 2: Try to parse table-like string format
        if '\n' in result_str and ('|' in result_str or '\t' in result_str):
            lines = result_str.strip().split('\n')
            
            # Look for separator line (usually contains dashes)
            data_lines = []
            header_found = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Skip separator lines with dashes
                if re.match(r'^[\-\+\|]+$', line):
                    header_found = True
                    continue
                
                # Process data lines
                if '|' in line:
                    # Split by pipe and clean
                    row_data = [cell.strip() for cell in line.split('|')]
                    # Remove empty first/last elements if they exist
                    row_data = [cell for cell in row_data if cell]
                    if row_data:
                        data_lines.append(row_data)
                elif '\t' in line:
                    # Split by tab
                    row_data = [cell.strip() for cell in line.split('\t')]
                    if row_data:
                        data_lines.append(row_data)
            
            if data_lines:
                # Use first line as headers if no header was found
                if not header_found and len(data_lines) > 1:
                    headers = data_lines[0]
                    data_rows = data_lines[1:]
                else:
                    # Extract column names from SQL
                    headers = extract_columns_from_sql(sql_query)
                    data_rows = data_lines
                
                # Ensure all rows have same length as headers
                max_cols = len(headers)
                processed_rows = []
                
                for row in data_rows:
                    # Pad or trim row to match header length
                    if len(row) < max_cols:
                        row.extend([''] * (max_cols - len(row)))
                    elif len(row) > max_cols:
                        row = row[:max_cols]
                    processed_rows.append(row)
                
                return pd.DataFrame(processed_rows, columns=headers)
        
        # Method 3: Handle single value results
        columns = extract_columns_from_sql(sql_query)
        
        # Try to parse as a simple value
        try:
            # Remove extra whitespace and quotes
            clean_result = result_str.strip('\'"')
            
            # If it's a number, try to convert
            try:
                if '.' in clean_result:
                    value = float(clean_result)
                else:
                    value = int(clean_result)
            except:
                value = clean_result
            
            # Create DataFrame with single value
            if len(columns) == 1:
                return pd.DataFrame([[value]], columns=columns)
            else:
                # Multiple columns but single result - put in first column
                row_data = [value] + [''] * (len(columns) - 1)
                return pd.DataFrame([row_data], columns=columns)
                
        except:
            pass
        
        # Fallback: Create a simple DataFrame with the raw result
        return pd.DataFrame([{'Result': result_str}])
        
    except Exception as e:
        # Final fallback - return error info
        columns = extract_columns_from_sql(sql_query) if sql_query else ['Result']
        return pd.DataFrame([{'Error': f"Failed to parse result: {str(e)}", 'Raw_Result': str(result_data)}])

def extract_columns_from_sql(sql_query):
    """
    Extract column names from SQL SELECT statement
    
    Args:
        sql_query (str): The SQL query
        
    Returns:
        list: List of column names
    """
    try:
        # Clean up the query
        query = sql_query.strip().upper()
        
        # Handle SELECT * queries
        if 'SELECT *' in query:
            # We can't determine exact columns from SELECT *, use generic names
            return ['Column_1', 'Column_2', 'Column_3', 'Column_4', 'Column_5']
        
        # Extract the SELECT portion
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return ['Result']
        
        select_part = select_match.group(1)
        
        # Split by comma and clean up
        columns = []
        column_parts = select_part.split(',')
        
        for part in column_parts:
            part = part.strip()
            
            # Handle aliases (AS keyword)
            if ' AS ' in part.upper():
                alias = part.upper().split(' AS ')[-1].strip()
                columns.append(alias.strip('"\''))
            else:
                # Remove function calls and get the base column name
                # Handle cases like COUNT(*), SUM(column), etc.
                if '(' in part and ')' in part:
                    func_match = re.search(r'(\w+)\s*\(', part)
                    if func_match:
                        func_name = func_match.group(1)
                        columns.append(func_name.title())
                    else:
                        columns.append('Result')
                else:
                    # Simple column name, remove table prefix if exists
                    col_name = part.split('.')[-1].strip('"\'')
                    columns.append(col_name)
        
        return columns if columns else ['Result']
        
    except Exception:
        return ['Result']

def export_results_to_csv():
    """Export all query results to CSV with proper formatting"""
    try:
        if not st.session_state.query_results:
            return None
        
        # Create a comprehensive CSV with all results
        all_data = []
        
        for i, query_data in enumerate(st.session_state.query_results, 1):
            # Parse the result into DataFrame
            df = parse_sql_result_to_dataframe(query_data['sql'], query_data['result'])
            
            # Add metadata columns
            df.insert(0, 'Query_Number', i)
            df.insert(1, 'Timestamp', query_data['timestamp'])
            df.insert(2, 'Question', query_data['question'])
            df.insert(3, 'SQL_Query', query_data['sql'])
            df.insert(4, 'Answer', query_data['answer'])
            
            all_data.append(df)
        
        # Combine all DataFrames
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True, sort=False)
        else:
            final_df = pd.DataFrame()
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        final_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error generating CSV: {str(e)}")
        return None

def export_current_result_to_csv():
    """Export current query result to CSV with proper column extraction"""
    try:
        if not st.session_state.last_result_data:
            return None
        
        # Parse the current result
        df = parse_sql_result_to_dataframe(
            st.session_state.last_result_data['sql'], 
            st.session_state.last_result_data['result']
        )
        
        # Add metadata as first row or separate sheet info
        metadata_df = pd.DataFrame([{
            'Metadata': 'Query Information',
            'Question': st.session_state.last_result_data['question'],
            'SQL_Query': st.session_state.last_result_data['sql'],
            'Timestamp': st.session_state.last_result_data['timestamp'],
            'Answer': st.session_state.last_result_data['answer']
        }])
        
        # Create final CSV with metadata and results
        csv_buffer = io.StringIO()
        
        # Write metadata first
        csv_buffer.write("# Query Metadata\n")
        metadata_df.to_csv(csv_buffer, index=False)
        csv_buffer.write("\n# Query Results\n")
        
        # Write actual results
        df.to_csv(csv_buffer, index=False)
        
        csv_buffer.seek(0)
        return csv_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error generating current result CSV: {str(e)}")
        return None

def export_result_data_only():
    """Export only the data results without metadata - clean format"""
    try:
        if not st.session_state.last_result_data:
            return None
        
        # Parse just the result data
        df = parse_sql_result_to_dataframe(
            st.session_state.last_result_data['sql'], 
            st.session_state.last_result_data['result']
        )
        
        # Convert to clean CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error generating data-only CSV: {str(e)}")
        return None


    
