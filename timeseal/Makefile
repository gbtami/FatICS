all: openseal openseal_decoder zipseal zipseal_decoder maketable \
	zipseal_encoder

CFLAGS = -g -Wall

openseal: openseal.c
	$(CC) -o openseal openseal.c

openseal_decoder: openseal_decoder.c
	$(CC) -o openseal_decoder openseal_decoder.c

zipseal: zipseal.c libhuffman.a
	$(CC) $(CFLAGS) -o zipseal zipseal.c libhuffman.a

zipseal_decoder: zipseal_decoder.c
	$(CC) $(CFLAGS) -o zipseal_decoder zipseal_decoder.c

zipseal_encoder: zipseal_encoder.c libhuffman.a
	$(CC) $(CFLAGS) -o zipseal_encoder zipseal_encoder.c libhuffman.a

compress: compress.c
	$(CC) -lz $(CFLAGS) -o compress compress.c

maketable: maketable.c bitarray.c bitfile.c huflocal.c
	$(CC) -O3 -Wall -o maketable maketable.c bitarray.c bitfile.c \
		huflocal.c

#chuffman: chuffman.o huflocal.o bitarray.o bitfile.o
#	$(CC) -g -Wall -o chuffman chuffman.o huflocal.o bitarray.o \
#		bitfile.o

huflocal.o: huflocal.c
	$(CC) -g -Wall -c huflocal.c
chuffman.o: chuffman.c codes.c
	$(CC) -g -Wall -c chuffman.c
bitarray.o: bitarray.c
	$(CC) -g -Wall -c bitarray.c
bitfile.o: bitfile.c
	$(CC) -g -Wall -c bitfile.c

libhuffman.a:   chuffman.o huflocal.o bitarray.o bitfile.o
	ar crsv libhuffman.a chuffman.o huflocal.o bitarray.o \
		bitfile.o

clean:
	rm -f openseal openseal_decoder zipseal zipseal_decoder *.o \
		libhuffman.a
