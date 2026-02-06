from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, regexp_replace, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, DateType, DoubleType

from udf_utils import *
from config.config import configuration


def define_udfs():
    """
    Registry for User Defined Functions.
    
    Performance Note: Python UDFs incur serialization overhead (pickling) between 
    the JVM and Python worker. While native Spark SQL functions are faster, 
    UDFs are necessary here for complex regex parsing of unstructured text.
    """
    return {
        'extract_file_name_udf': udf(extract_file_name, StringType()),
        'extract_position_udf': udf(extract_position, StringType()),

        # Optimization: Return a StructType to extract multiple related fields 
        # in a single pass, avoiding redundant regex execution.
        'extract_salary_udf': udf(extract_salary, StructType([
            StructField('salary_start', DoubleType(), True),
            StructField('salary_end', DoubleType(), True)
        ])),
        'extract_date_udf': udf(extract_start_date, DateType()),
        'extract_classcode_udf': udf(extract_class_code, StringType()),
        'extract_requirements_udf': udf(extract_requirements, StringType()),
        'extract_notes_udf': udf(extract_notes, StringType()),
        'extract_duties_udf': udf(extract_duties, StringType()),
        'extract_enddate_udf': udf(extract_end_date, DateType()),
        'extract_selection_udf': udf(extract_selection, StringType()),
        'extract_experience_length_udf': udf(extract_experience_length, StringType()),
        'extract_education_length_udf': udf(extract_education_length, StringType()),
        'extract_application_location_udf': udf(extract_application_location, StringType()),

    }


if __name__ == "__main__":
    # Infrastructure & Dependency Management
    # explicitly defining Maven coordinates prevents dependency conflicts.
    #
    # Security Warning: In production, avoid hardcoding keys. Use 
    # 'InstanceProfileCredentialsProvider' (IAM Roles) for better security.
    # SimpleAWSCredentialsProvider is used here for explicit local dev auth.
    spark = (
        SparkSession.builder.appName("AWS_Spark_Unstructured_Streaming") 
            .config('spark.jars.packages',
                    'org.apache.hadoop:hadoop-aws:3.3.1,'
                    'com.amazonaws:aws-java-sdk:1.11.469')
            .config('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
            .config('spark.hadoop.fs.s3a.access.key', configuration.get('AWS_ACCESS_KEY'))
            .config('spark.hadoop.fs.s3a.secret.key', configuration.get('AWS_SECRET_KEY'))
            .config('spark.hadoop.fs.s3a.aws.credentials.provider', 'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider')
            .getOrCreate()
    )

    text_input_dir = r'D:\Programming\DE\AWS Realtime\input\input_text'
    json_input_dir = r'D:\Programming\DE\AWS Realtime\input\input_json'
    pdf_input_dir = r'D:\Programming\DE\AWS Realtime\input\input_pdf'
    video_input_dir = r'D:\Programming\DE\AWS Realtime\input\input_video'
    csv_input_dir = r'D:\Programming\DE\AWS Realtime\input\input_csv'
    image_input_dir = r'D:\Programming\DE\AWS Realtime\input\input_image'


    # Performance: Schema Enforcement
    # Defining schema explicitly prevents Spark from inferring it (expensive operation).
    # It also ensures pipeline stability by failing fast on malformed data types.
    data_schema = StructType([
        StructField('file_name', StringType(), True),
        StructField('position', StringType(), True),
        StructField('classcode', StringType(), True),
        StructField('salary_start', DoubleType(), True),
        StructField('salary_end', DoubleType(), True),
        StructField('start_date', DateType(), True),
        StructField('end_date', DateType(), True),
        StructField('req', StringType(), True),
        StructField('notes', StringType(), True),
        StructField('duties', StringType(), True),
        StructField('selection', StringType(), True),
        StructField('experience_length', StringType(), True),
        StructField('job_type', StringType(), True),
        StructField('education_length', StringType(), True),
        StructField('school_type', StringType(), True),
        StructField('application_location', StringType(), True)
    ])


    udfs = define_udfs()


    # Data Ingestion: Text Stream
    # 'wholetext' reads the entire file content into a single row. 
    # Risk: May cause OOM (Out of Memory) if individual source files are massive.
    job_bulletins_df = (
        spark.readStream
            .format('text')
            .option('wholetext', 'true')
            .load(text_input_dir)
    )

    # Data Ingestion: JSON Stream
    # 'multiLine' loads the whole JSON object into memory to parse.
    # Ensure input file sizes fit within Executor memory limits.
    json_df = (
        spark.readStream
            .json('input_json', schema=data_schema, multiLine=True)
    )


    # Transformation Pipeline
    # 1. Pre-processing: Clean newlines/returns to ensure regex consistency.
    # 2. Extraction: Apply Python UDFs to parse unstructured text.
    # 3. Struct Unpacking: Extract specific fields from UDF results.
    job_bulletins_df = ( 
        job_bulletins_df.withColumn('file_name', regexp_replace(udfs['extract_file_name_udf']('value'), '\r', ' '))
                        .withColumn('value', regexp_replace(regexp_replace('value', r'\n', ' '), r'\r', ' '))
                        .withColumn('position', regexp_replace(udfs['extract_position_udf']('value'), '\r', ' '))
                        .withColumn('salary_start', udfs['extract_salary_udf']('value').getField('salary_start'))
                        .withColumn('salary_end', udfs['extract_salary_udf']('value').getField('salary_end'))
                        .withColumn('start_date', udfs['extract_date_udf']('value'))
                        .withColumn('end_date', udfs['extract_enddate_udf']('value'))
                        .withColumn('classcode', udfs['extract_classcode_udf']('value'))
                        .withColumn('req', udfs['extract_requirements_udf']('value'))
                        .withColumn('notes', udfs['extract_notes_udf']('value'))
                        .withColumn('duties', udfs['extract_duties_udf']('value'))
                        .withColumn('selection', udfs['extract_selection_udf']('value'))
                        .withColumn('experience_length', udfs['extract_experience_length_udf']('value'))
                        .withColumn('education_length', udfs['extract_education_length_udf']('value'))
                        .withColumn('application_location', udfs['extract_application_location_udf']('value'))
    )

    # Select the data from text file
    job_bulletins_df = job_bulletins_df.select('file_name', 'start_date', 'end_date', 'salary_start', 'salary_end', \
                                               'classcode', 'req', 'notes', 'duties', 'selection', 'experience_length', \
                                                'education_length', 'application_location')

    # Select the data from json file
    json_df = json_df.select('file_name', 'start_date', 'end_date', 'salary_start', 'salary_end', \
                                               'classcode', 'req', 'notes', 'duties', 'selection', 'experience_length', \
                                                'education_length', 'application_location')

    # Merge streams into a unified dataset
    union_df = job_bulletins_df.union(json_df)


    # create the streamWriter function
    def stream_writer(input: DataFrame, checkpoint_folder, output):
        return (input.writeStream
                    .format('parquet')
                    # Reliability: Checkpointing
                    # Critical for Fault Tolerance. Allows the stream to recover 
                    # from failure and resume from the last processed offset.
                    .option('checkpointLocation', checkpoint_folder)
                    .option('path', output)
                    .outputMode('append')
                    .trigger(processingTime='5 seconds')
                    .start()
                )
    

    # query=  (
    #     union_df.writeStream
    #         .outputMode('append')
    #         .format('console')
    #         .option('truncate', False)  # check all the data
    #         .start()
    # )

    query = stream_writer(union_df, 's3a://my-spark-s3-unstructured-streaming/checkpoints/', 's3a://my-spark-s3-unstructured-streaming/data/spark_unstructured')

    query.awaitTermination()


    spark.stop()