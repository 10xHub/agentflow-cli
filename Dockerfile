FROM python:3.12

# SET ENV
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# set work directory
WORKDIR /app

# First install with root
RUN apt update -y

# install dependencies
COPY requirements.txt .

## now create virtualenv
#ENV VIRTUAL_ENV=/venv
#RUN python3 -m venv $VIRTUAL_ENV
#RUN ls $VIRTUAL_ENV
#ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# copy project
COPY . .
