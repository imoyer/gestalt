import io

if __name__ == '__main__':
	f = open('test.csv', 'r')
	airfoil = []

	for line in f.readlines():
		xy = line.split(' ')
		coor = []
		for num in xy:
			coor.append(float(num))
		airfoil.append(coor)
	
	airfoil2 = airfoil[0:70]
	airfoil1 = airfoil[70:]

	airfoilmoves = []
	for coord in airfoil1:
		airfoilmoves.append([coord[0], coord[1], coord[0], coord[1]])
	for coord in airfoil2:
		airfoilmoves.append([coord[0], coord[1], coord[0], coord[1]])
	airfoilmoves.append([0,0,0,0])
	
	for move in airfoilmoves:
		print move
