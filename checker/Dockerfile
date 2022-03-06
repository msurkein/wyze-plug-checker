FROM public.ecr.aws/lambda/python:3.9
EXPOSE 8080/tcp
# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Install the function's dependencies using file requirements.txt
# from your project folder.
# RUN yum -y groups mark install "Development Tools" && yum -y groups mark convert "Development Tools" && yum -y group install "Development Tools"

COPY requirements.txt  .
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "app.handler" ]